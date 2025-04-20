#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改服务模块
提供作文批改相关功能
"""

import os
import logging
import datetime
import json
import time
from typing import Dict, Any, List, Optional, Union
import uuid
import traceback
import re
import random

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from dependency_injector.wiring import inject, Provide

from app.config import config
from app.utils import get_file_handler
from app.core.user.user_service import UserService
from app.models.essay import Essay, EssayStatus
from app.models.user import User, MembershipLevel
from app.models.db import db
from app.models.correction import Correction, CorrectionStatus, CorrectionType
from app.core.correction.ai_corrector import AICorrectionService
from app.core.ai.open_ai_client import OpenAIClient
from app.core.correction.report_generator import ReportGenerator
from app.core.correction.correction_logger import correction_logger
from app.extensions import db
from app.utils.exceptions import (
    ResourceNotFoundError, ValidationError, 
    LimitExceededError, ServiceUnavailableError, PermissionDeniedError, BusinessError
)
# 导入接口定义
from app.core.correction.interface import ICorrectionService

logger = logging.getLogger(__name__)

class CorrectionService(ICorrectionService):
    """作文批改服务类"""
    
    def __init__(self):
        """初始化批改服务"""
        self.ai_corrector = AICorrectionService()
        self.user_service = UserService()
        self.file_handler = get_file_handler()
        self.supported_extensions = ['txt', 'docx', 'pdf', 'jpg', 'jpeg', 'png']
        self.max_essay_length = 10000  # 最大字符数
        self.debug_mode = bool(os.environ.get('DEBUG_MODE', False))
        self.temp_files = {}  # 用于保存临时文件路径的字典
        
        # 获取文件服务
        try:
            from app.core.services.container import container
            self.file_service = container.get("file_service")
            if not self.file_service:
                logger.warning("未找到文件服务，尝试从服务注册表获取")
                from app.core.services.service_registry_di import ServiceContainer
                # 尝试从依赖注入容器获取
                self.file_service = ServiceContainer.file_service()
        except Exception as e:
            logger.warning(f"获取文件服务失败: {str(e)}，将使用内存缓存管理文件信息")
            self.file_service = None
        
        # 日志初始化
        debug_str = "调试模式开启" if self.debug_mode else "调试模式关闭"
        logger.info(f"批改服务初始化完成，{debug_str}")
        
        self.report_generator = ReportGenerator()
        self.logger = correction_logger
        
        # 检查API密钥是否配置
        self._check_api_keys()
    
    def _check_api_keys(self):
        # 检查API密钥是否配置
        env_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        if not env_api_key or env_api_key == 'your_api_key_here':
            logger.warning("未配置DeepSeek API密钥或密钥无效，将使用调试模式")
            # 强制启用调试模式
            if hasattr(self.ai_corrector, 'debug_mode'):
                self.ai_corrector.debug_mode = True
        
        logger.info(f"批改服务初始化完成，调试模式: {getattr(self.ai_corrector, 'debug_mode', False)}")
    
    def check_user_limits(self, user_id: int) -> Dict[str, Any]:
        """
        检查用户是否达到作文批改限制
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 检查结果，包含以下字段：
                - status: 'success' 或 'error'
                - message: 错误信息（如果有）
                - daily_usage: 今日已使用次数
                - daily_limit: 每日限制
                - monthly_usage: 本月已使用次数
                - monthly_limit: 每月限制
                - can_submit: 是否可以提交
                - membership_level: 会员等级
                - is_subscription_active: 是否有活跃订阅
        """
        try:
            # 获取用户信息
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                return {'status': 'error', 'message': '用户不存在'}
            
            # 管理员用户不受限制
            if user.is_admin:
                logger.info(f"管理员用户 {user_id} 不受批改次数限制")
                return {
                    'status': 'success',
                    'message': None,
                    'daily_usage': 0,
                    'daily_limit': float('inf'),  # 无限制
                    'monthly_usage': 0,
                    'monthly_limit': float('inf'),  # 无限制
                    'can_submit': True,
                    'membership_level': user.membership_level,
                    'is_subscription_active': True
                }
            
            # 获取用户资料
            profile = user.profile
            if not profile:
                return {'status': 'error', 'message': '用户资料不存在'}
            
            # 获取用户限制配置
            limits = profile.get_essay_limits()
            daily_limit = limits['daily']
            monthly_limit = limits['monthly']
            
            # 计算今日已提交的作文数量
            today = datetime.datetime.now().date()
            today_start = datetime.datetime.combine(today, datetime.time.min)
            today_end = datetime.datetime.combine(today, datetime.time.max)
            
            daily_count = Essay.query.filter(
                Essay.user_id == user_id,
                Essay.created_at.between(today_start, today_end)
            ).count()
            
            # 计算本月已提交的作文数量
            month_start = datetime.datetime(today.year, today.month, 1)
            month_end = (datetime.datetime(today.year, today.month + 1, 1) 
                         if today.month < 12 
                         else datetime.datetime(today.year + 1, 1, 1)) - datetime.timedelta(days=1)
            month_end = datetime.datetime.combine(month_end, datetime.time.max)
            
            monthly_count = Essay.query.filter(
                Essay.user_id == user_id,
                Essay.created_at.between(month_start, month_end)
            ).count()
            
            # 检查是否超过限制
            can_submit = True
            message = None
            
            if daily_count >= daily_limit:
                can_submit = False
                message = f'您今日批改已达上限({daily_limit}篇)，请明天再试或升级会员'
            elif monthly_count >= monthly_limit:
                can_submit = False
                message = f'您本月批改已达上限({monthly_limit}篇)，请下月再试或升级会员'
            
            return {
                'status': 'success',
                'message': message,
                'daily_usage': daily_count,
                'daily_limit': daily_limit,
                'monthly_usage': monthly_count,
                'monthly_limit': monthly_limit,
                'can_submit': can_submit,
                'membership_level': user.membership_level,
                'is_subscription_active': profile.is_subscription_active()
            }
        
        except Exception as e:
            logger.error(f"检查用户限制时发生错误: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'检查用户限制时发生错误: {str(e)}'}
    
    def _get_or_create_correction(self, essay_id: int, correction_type: str = CorrectionType.AI.value) -> Correction:
        """
        获取或创建批改记录
        如果已存在未删除的记录，则返回已有记录，否则创建新记录
        
        Args:
            essay_id: 作文ID
            correction_type: 批改类型，默认为AI批改
            
        Returns:
            Correction: 批改记录对象
        """
        # 查找已存在的未删除记录
        existing = Correction.query.filter_by(
            essay_id=essay_id, 
            is_deleted=False
        ).first()
        
        if existing:
            logger.info(f"找到作文ID={essay_id}的现有批改记录，ID={existing.id}")
            return existing
        
        # 创建新记录
        correction = Correction(
            essay_id=essay_id,
            status=CorrectionStatus.PENDING.value,
            type=correction_type,
            created_at=datetime.datetime.now(),
            is_deleted=False
        )
        db.session.add(correction)
        db.session.flush()
        logger.info(f"为作文ID={essay_id}创建新批改记录，ID={correction.id}")
        
        return correction
    
    def submit_essay(self, user_id: int, title: str, content: str, grade: str = 'junior') -> Dict[str, Any]:
        """
        提交作文进行批改
        
        Args:
            user_id: 用户ID
            title: 作文标题
            content: 作文内容
            grade: 年级水平 (primary, junior, senior, college)
        
        Returns:
            Dict: 提交结果，包含status、message、essay_id等信息
        """
        try:
            # 检查用户限制
            limits = self.check_user_limits(user_id)
            if not limits.get('can_submit', False):
                return {
                    'status': 'error',
                    'message': '您已达到批改次数限制，请升级会员或等待次日继续使用'
                }
            
            # 创建参数字典，并过滤无效参数
            create_params = {
                'user_id': user_id,
                'title': title,
                'content': content,
                'grade': grade,
                'status': EssayStatus.PENDING.value,
                'created_at': datetime.datetime.now(),
                'updated_at': datetime.datetime.now(),
                'source_type': 'text'  # 添加默认的source_type字段值
            }
            
            # 只保留Essay模型中实际存在的字段
            valid_params = {k:v for k,v in create_params.items() if hasattr(Essay, k)}
            logger.info(f"准备创建Essay，参数: {valid_params}")
            
            # 延迟导入任务函数，避免循环导入
            from app.tasks.correction_tasks import process_essay_correction
            
            # 使用事务创建Essay对象并启动任务
            task_id = None
            essay_id = None
            
            try:
                # 创建Essay对象
                essay = Essay(**valid_params)
                db.session.add(essay)
                db.session.flush()  # 获取ID但不提交事务
                
                essay_id = essay.id
                logger.info(f"创建作文记录，ID: {essay_id}")
                
                # 验证记录是否成功创建
                if not essay_id:
                    raise ValueError("作文记录创建失败，无法获取有效ID")
                
                # 创建批改记录
                correction = self._get_or_create_correction(essay_id)
                
                # 提交事务以保证数据持久化
                db.session.commit()
                logger.info(f"已提交数据库事务，再次检查Essay ID: {essay_id}是否存在")
                
                # 验证记录是否成功保存
                check_essay = Essay.query.filter_by(id=essay_id).first()
                if not check_essay:
                    logger.error(f"严重错误：数据库提交后无法找到Essay ID: {essay_id}")
                    # 如果找不到记录，返回错误，不启动任务
                    return {
                        'status': 'error',
                        'message': '作文提交成功但在数据库中找不到，请联系管理员',
                        'essay_id': essay_id
                    }
                else:
                    logger.info(f"验证成功：找到Essay ID: {essay_id}, 标题: {check_essay.title}")
                
                # 确保数据已经写入数据库并可被其他进程访问
                db.session.flush()
                
                # 添加延迟，确保数据完全写入数据库
                time.sleep(0.5)
                
                # 启动异步批改任务
                logger.info(f"准备调用 process_essay_correction.delay 发送任务，essay_id: {essay_id}")
                task_result = None
                try:
                    # 显式指定队列为 'correction'，确保发送到正确的队列
                    task_result = process_essay_correction.apply_async(args=[essay_id], queue='correction')
                    task_id = task_result.id
                    logger.info(f"process_essay_correction.apply_async 调用成功，task_id: {task_id}")
                except Exception as task_send_error:
                    logger.error(f"调用 process_essay_correction.apply_async 时发生错误: {str(task_send_error)}", exc_info=True)
                    # 如果任务发送失败，也应该回滚数据库并返回错误
                    db.session.rollback()
                    return {
                        'status': 'error',
                        'message': f'发送批改任务失败: {str(task_send_error)}',
                        'essay_id': essay_id
                    }
                
                # 确保获得了任务ID
                if not task_id:
                    # 这通常不应该发生，除非 apply_async 本身返回异常（已在上面捕获）或返回空结果
                    logger.error(f"严重错误：未能获取任务ID，即使 apply_async 没有报错，作文ID: {essay_id}")
                    db.session.rollback() # 可能需要回滚之前的数据库操作
                    return {
                        'status': 'error',
                        'message': '发送批改任务后未能获取任务ID，请联系管理员',
                        'essay_id': essay_id
                    }
                
                # 更新批改记录的task_id
                correction.task_id = task_id
                db.session.commit()
                
                logger.info(f"成功提交作文批改任务，essay_id: {essay_id}, task_id: {task_id}")
                
            except SQLAlchemyError as db_error:
                db.session.rollback()
                logger.error(f"数据库操作失败: {str(db_error)}", exc_info=True)
                return {
                    'status': 'error',
                    'message': f'数据库操作失败，请重试: {str(db_error)}'
                }
            
            # 返回结果
            return {
                'status': 'success',
                'message': '作文已提交并开始批改',
                'essay_id': essay_id,
                'task_id': task_id
            }
            
        except Exception as e:
            logger.error(f"提交作文时发生错误: {str(e)}", exc_info=True)
            # 确保任何未处理的事务都会回滚
            try:
                db.session.rollback()
            except:
                pass
                
            return {
                'status': 'error',
                'message': f'提交作文时发生错误: {str(e)}'
            }
    
    def submit_essay_file(self, user_id: int, title: str, file_data, filename: str) -> Dict[str, Any]:
        """
        上传文件提交作文进行批改
        
        Args:
            user_id: 用户ID
            title: 作文标题
            file_data: 文件数据
            filename: 文件名
        
        Returns:
            Dict: 提交结果
        """
        # Import task inside the method to break circular dependency
        from app.tasks.correction_tasks import process_essay_correction 
        try:
            # 检查参数
            if not title or not file_data or not filename:
                return {'status': 'error', 'message': '标题和文件不能为空'}
            
            # 检查用户权限和限制
            limits_check = self.check_user_limits(user_id)
            if limits_check['status'] != 'success':
                return limits_check
            
            if not limits_check['can_submit']:
                return {
                    'status': 'error', 
                    'message': '您已达到作文批改限制，请升级会员或等待下个周期',
                    'limits': limits_check
                }
            
            # 处理文件
            file_result = self.file_handler.process_file(file_data, filename)
            if not file_result:
                return {'status': 'error', 'message': '不支持的文件类型或处理文件时出错'}
            
            # 检查内容长度
            content = file_result['content']
            if len(content) > self.max_essay_length:
                # 清理临时文件
                if file_result['path'] and os.path.exists(file_result['path']):
                    self.file_handler.delete_file(file_result['path'])
                return {'status': 'error', 'message': f'作文超过最大长度限制（{self.max_essay_length}字符）'}
            
            # 创建新的作文记录
            essay = Essay(
                user_id=user_id,
                title=title,
                content=content,
                status=EssayStatus.PENDING.value,
                source_type=file_result['source_type']
            )
            
            db.session.add(essay)
            db.session.commit()
            
            # 验证记录是否成功保存
            essay_id = essay.id
            check_essay = Essay.query.filter_by(id=essay_id).first()
            if not check_essay:
                logger.error(f"严重错误：数据库提交后无法找到Essay ID: {essay_id}")
                return {
                    'status': 'error',
                    'message': '作文提交成功但在数据库中找不到，请联系管理员',
                    'essay_id': essay_id
                }
            
            # 保存文件元数据
            if self.file_service:
                # 使用文件服务管理文件元数据
                self.file_service.create_file_metadata(essay_id, file_result)
                logger.debug(f"已使用文件服务保存元数据，作文ID: {essay_id}")
            else:
                # 使用临时解决方案
                self._save_temp_file_info(essay_id, file_result['path'])
            
            # 确保数据已经写入数据库并可被其他进程访问
            db.session.flush()
            
            # 添加延迟，确保数据完全写入数据库
            time.sleep(0.5)
            
            # 异步处理批改任务
            process_essay_correction.delay(essay.id)
            
            # 返回结果
            result = self._create_success_result(essay, None)
            
            # 记录提交成功
            logger.info(f"用户 {user_id} 以文件上传方式提交作文成功，ID: {essay.id}")
            
            return result
        
        except Exception as e:
            logger.error(f"提交作文文件时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
            return {'status': 'error', 'message': f'提交作文文件时发生错误: {str(e)}'}
    
    def get_essay(self, essay_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取作文信息
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID（可选，用于权限检查）
        
        Returns:
            Dict: 作文信息
        """
        try:
            # 查询作文
            essay = Essay.query.get(essay_id)
            if not essay:
                return {'status': 'error', 'message': '作文不存在'}
            
            # 如果提供了用户ID，检查权限
            if user_id is not None and essay.user_id != user_id:
                # 检查是否为管理员
                user = self.user_service.get_user_by_id(user_id)
                if not user or not user.is_admin:
                    return {'status': 'error', 'message': '无权访问此作文'}
            
            # 构造返回数据
            essay_data = {
                'id': essay.id,
                'title': essay.title,
                'status': essay.status,
                'source_type': essay.source_type,
                'user_id': essay.user_id,
                'created_at': essay.created_at.isoformat() if essay.created_at else None,
                'updated_at': essay.updated_at.isoformat() if essay.updated_at else None
            }
            
            # 如果已批改完成，添加批改结果
            if essay.status == EssayStatus.COMPLETED.value:
                essay_data.update({
                    'score': essay.score,
                    'corrected_content': essay.corrected_content,
                    'comments': essay.comments,
                    'error_analysis': essay.error_analysis,
                    'improvement_suggestions': essay.improvement_suggestions
                })
            
            return {
                'status': 'success',
                'essay': essay_data
            }
        
        except Exception as e:
            logger.error(f"获取作文信息时发生错误: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'获取作文信息时发生错误: {str(e)}'}
    
    def get_user_essays(self, user_id: int, page: int = 1, per_page: int = 10, 
                        status: Optional[str] = None) -> Dict[str, Any]:
        """
        获取用户的作文列表
        
        Args:
            user_id: 用户ID
            page: 页码
            per_page: 每页数量
            status: 作文状态过滤
        
        Returns:
            Dict: 作文列表
        """
        try:
            # 构建查询
            query = Essay.query.filter(Essay.user_id == user_id)
            
            # 根据状态过滤
            if status:
                query = query.filter(Essay.status == status)
            
            # 分页
            total = query.count()
            essays = query.order_by(Essay.created_at.desc())\
                         .offset((page - 1) * per_page)\
                         .limit(per_page)\
                         .all()
            
            # 构造返回数据
            essay_list = []
            for essay in essays:
                essay_data = {
                    'id': essay.id,
                    'title': essay.title,
                    'status': essay.status,
                    'source_type': essay.source_type,
                    'created_at': essay.created_at.isoformat() if essay.created_at else None,
                    'updated_at': essay.updated_at.isoformat() if essay.updated_at else None
                }
                essay_list.append(essay_data)
            
            return {
                'status': 'success',
                'essays': essay_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        
        except Exception as e:
            logger.error(f"获取用户作文列表时发生错误: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'获取用户作文列表时发生错误: {str(e)}'}
    
    def delete_essay(self, essay_id: int, user_id: int) -> Dict[str, Any]:
        """
        删除作文
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID
        
        Returns:
            Dict: 删除结果
        """
        try:
            # 查询作文
            essay = Essay.query.get(essay_id)
            if not essay:
                return {'status': 'error', 'message': '作文不存在'}
            
            # 检查权限
            if essay.user_id != user_id:
                # 检查是否为管理员
                user = self.user_service.get_user_by_id(user_id)
                if not user or not user.is_admin:
                    return {'status': 'error', 'message': '无权删除此作文'}
            
            # 删除关联的文件
            if self.file_service:
                # 使用文件服务删除文件
                self.file_service.delete_file(essay_id)
            else:
                # 使用临时方法
                self._remove_temp_file(essay_id)
            
            # 删除作文记录
            db.session.delete(essay)
            db.session.commit()
            
            return {
                'status': 'success',
                'message': '作文已删除'
            }
        
        except Exception as e:
            logger.error(f"删除作文时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
            return {'status': 'error', 'message': f'删除作文时发生错误: {str(e)}'}
    
    @correction_logger.monitor_correction
    def perform_correction(self, essay_id: Union[int, Essay]) -> Dict[str, Any]:
        """
        执行作文批改
        
        Args:
            essay_id: 作文ID或Essay对象
            
        Returns:
            Dict: 批改结果
        """
        essay = None
        correction = None
        
        try:
            # 获取作文对象
            essay = essay_id if isinstance(essay_id, Essay) else Essay.query.get(essay_id)
            if not essay:
                logger.error(f"作文不存在，ID: {essay_id}")
                return {
                    "status": "error",
                    "message": f"作文不存在，ID: {essay_id}"
                }

            # 在事务中创建或获取批改记录，并更新状态
            try:
                # 开始外部事务
                db.session.begin()
                
                # 获取或创建批改记录
                correction = self._get_or_create_correction(essay.id)
                
                # 记录开始批改
                logger.info(f"开始批改作文 [ID: {essay.id}, 标题: {essay.title}]")
                
                # 更新作文状态为批改中
                essay.status = EssayStatus.CORRECTING.value
                correction.status = CorrectionStatus.CORRECTING.value
                correction.updated_at = datetime.datetime.now()
                
                # 提交事务
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"初始化批改状态失败: {str(e)}")
                return {
                    "status": "error",
                    "message": f"初始化批改状态失败: {str(e)}"
                }

            # 调用AI批改
            logger.info(f"调用AI批改服务，作文ID: {essay.id}")
            correction_data = self._perform_ai_correction(essay.content)
            
            # 检查AI返回结果状态
            if correction_data.get("status") != "success":
                error_msg = correction_data.get("message", "AI返回结果状态错误")
                logger.error(f"AI批改失败 [ID: {essay.id}] - {error_msg}")
                
                # 在新事务中更新作文状态为失败
                try:
                    db.session.begin()
                    
                    essay.status = EssayStatus.FAILED.value
                    essay.error_message = error_msg
                    
                    # 同步更新批改记录状态
                    correction.status = CorrectionStatus.FAILED.value
                    correction.error_message = error_msg
                    correction.updated_at = datetime.datetime.now()
                    
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"更新失败状态时发生错误: {str(e)}")
                
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            # 获取AI返回的数据
            result_data = correction_data.get("data", {})
            if not result_data:
                error_msg = "AI返回结果数据为空"
                logger.error(f"AI批改失败 [ID: {essay.id}] - {error_msg}")
                
                # 在新事务中更新作文状态为失败
                try:
                    db.session.begin()
                    
                    essay.status = EssayStatus.FAILED.value
                    essay.error_message = error_msg
                    
                    # 同步更新批改记录状态
                    correction.status = CorrectionStatus.FAILED.value
                    correction.error_message = error_msg
                    correction.updated_at = datetime.datetime.now()
                    
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"更新失败状态时发生错误: {str(e)}")
                
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            # 在新事务中更新作文和批改记录
            try:
                db.session.begin()
                
                logger.info(f"更新作文信息，ID: {essay.id}")
                
                # 基本信息
                essay.score = result_data.get("score", 0)
                essay.corrected_content = essay.content  # 保持原文不变
                essay.comments = result_data.get("feedback", "")
                
                # 错误分析
                error_analysis = {}
                if isinstance(result_data.get("error_analysis"), str):
                    try:
                        error_analysis = json.loads(result_data.get("error_analysis", "{}"))
                    except json.JSONDecodeError:
                        logger.warning(f"解析错误分析JSON失败，使用空对象")
                        error_analysis = {}
                else:
                    error_analysis = result_data.get("error_analysis", {})
                
                essay.error_analysis = json.dumps(error_analysis, ensure_ascii=False)
                essay.improvement_suggestions = result_data.get("improvement_suggestions", "")
                
                # 分项得分
                details = result_data.get("details", {})
                essay.content_score = details.get("content_score", 0)
                essay.language_score = details.get("language_score", 0)
                essay.structure_score = details.get("structure_score", 0)
                essay.writing_score = details.get("writing_score", 0)
                
                # 更新作文状态
                essay.status = EssayStatus.COMPLETED.value
                
                # 同步更新批改记录
                correction.results = json.dumps(result_data, ensure_ascii=False)
                correction.score = essay.score
                correction.comments = essay.comments
                correction.error_analysis = essay.error_analysis
                correction.improvement_suggestions = essay.improvement_suggestions
                correction.status = CorrectionStatus.COMPLETED.value
                correction.updated_at = datetime.datetime.now()
                correction.completed_at = datetime.datetime.now()
                
                # 提交事务
                db.session.commit()
                
                logger.info(f"AI批改完成，作文ID: {essay.id}, 得分: {essay.score}")
                return {
                    "status": "success",
                    "message": "批改成功",
                    "essay_id": essay.id,
                    "score": essay.score
                }
            except Exception as update_err:
                db.session.rollback()
                logger.error(f"更新作文信息失败 [ID: {essay.id}]: {str(update_err)}")
                logger.error(traceback.format_exc())
                
                # 再次尝试，只更新状态
                try:
                    db.session.begin()
                    
                    # 更新作文状态为失败
                    essay.status = EssayStatus.FAILED.value
                    essay.error_message = f"更新作文信息失败: {str(update_err)}"
                    
                    # 同步更新批改记录状态
                    correction.status = CorrectionStatus.FAILED.value
                    correction.error_message = f"更新作文信息失败: {str(update_err)}"
                    correction.updated_at = datetime.datetime.now()
                    
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"设置失败状态时出错: {str(e)}")
                
                return {
                    "status": "error",
                    "message": f"更新作文信息失败: {str(update_err)}"
                }

        except json.JSONDecodeError as je:
            error_msg = f"解析AI返回结果JSON失败: {str(je)}"
            logger.error(f"批改作文失败 [ID: {essay_id if not isinstance(essay_id, Essay) else essay_id.id}] - {error_msg}")
            
            # 更新状态
            self._set_error_status(essay, correction, error_msg)
                
            return {
                "status": "error",
                "message": error_msg
            }
            
        except Exception as e:
            error_msg = f"批改作文失败: {str(e)}"
            logger.error(f"批改作文失败 [ID: {essay_id if not isinstance(essay_id, Essay) else (essay.id if essay else 'Unknown')}] - {error_msg}")
            logger.error(traceback.format_exc())
            
            # 更新状态
            self._set_error_status(essay, correction, error_msg)
                
            return {
                "status": "error",
                "message": error_msg
            }
    
    def _set_error_status(self, essay, correction, error_msg):
        """设置错误状态，确保作文和批改记录状态一致"""
        try:
            db.session.begin()
            
            if essay:
                essay.status = EssayStatus.FAILED.value
                essay.error_message = error_msg
                
            if correction:
                correction.status = CorrectionStatus.FAILED.value
                correction.error_message = error_msg
                correction.updated_at = datetime.datetime.now()
                
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"设置错误状态失败: {str(e)}")
            logger.error(traceback.format_exc())
    
    def get_supported_file_types(self) -> Dict[str, Any]:
        """
        获取支持的文件类型
        
        Returns:
            Dict: 支持的文件类型
        """
        return {
            'status': 'success',
            'supported_extensions': self.supported_extensions
        }

    def get_correction_result(self, essay_id):
        """
        获取批改结果
        
        Args:
            essay_id: 作文ID
            
        Returns:
            dict: 批改结果
        """
        try:
            correction = Correction.query.filter_by(essay_id=essay_id).first()
            
            if not correction:
                return {
                    "status": "error",
                    "message": f"未找到批改记录，作文ID: {essay_id}"
                }
            
            # 如果结果仍在处理中
            if correction.status == 'processing':
                return {
                    "status": "processing",
                    "message": "批改仍在进行中",
                    "essay_id": essay_id
                }
            
            # 如果批改失败
            if correction.status == 'failed':
                error_message = "批改失败"
                if correction.extra_data and 'error' in correction.extra_data:
                    error_message = correction.extra_data['error']
                
                return {
                    "status": "error",
                    "message": error_message,
                    "essay_id": essay_id
                }
            
            # 如果批改完成但没有结果数据
            if correction.status == 'completed' and not correction.results:
                return {
                    "status": "error",
                    "message": "批改完成但结果数据丢失",
                    "essay_id": essay_id
                }
            
            # 返回批改结果
            try:
                results = json.loads(correction.results) if isinstance(correction.results, str) else correction.results
                return {
                    "status": "success",
                    "essay_id": essay_id,
                    "correction_id": correction.id,
                    "results": results
                }
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": "批改结果数据格式错误",
                    "essay_id": essay_id
                }
            
        except Exception as e:
            logger.error(f"获取批改结果失败，作文ID: {essay_id}, 错误: {str(e)}\n{traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"获取批改结果时发生错误: {str(e)}",
                "essay_id": essay_id
            }

    def _create_success_result(self, essay: Essay) -> Dict[str, Any]:
        """
        创建成功的返回结果
        
        Args:
            essay: Essay对象
            
        Returns:
            Dict: 包含作文信息和批改结果的字典
        """
        essay_data = {
            "essay_id": essay.id,
            "title": essay.title,
            "content": essay.content,
            "status": essay.status,
            "created_at": essay.created_at.isoformat() if essay.created_at else None,
            "updated_at": essay.updated_at.isoformat() if essay.updated_at else None
        }
        
        # 如果作文状态为已完成，添加批改结果
        if essay.status == EssayStatus.COMPLETED.value:
            essay_data.update({
                "score": essay.score,
                "corrected_text": essay.corrected_content,  # 保持与前端兼容
                "feedback": essay.comments,  # 保持与前端兼容
                "errors": essay.error_analysis,  # 保持与前端兼容
                "improvement_suggestions": essay.improvement_suggestions
            })
        
        # 获取最新的批改记录
        correction = Correction.query.filter_by(
            essay_id=essay.id,
            is_deleted=False
        ).order_by(Correction.created_at.desc()).first()
        
        if correction:
            essay_data["correction_id"] = correction.id
            essay_data["correction_status"] = correction.status
            
            # 如果批改完成，添加详细结果
            if correction.status == 'completed':
                try:
                    detailed_results = json.loads(correction.results) if correction.results else {}
                    essay_data["detailed_results"] = detailed_results
                except json.JSONDecodeError:
                    logger.warning(f"无法解析批改详细结果 JSON，作文ID: {essay.id}")
                    essay_data["detailed_results"] = {}
        
        return {
            "status": "success",
            "data": essay_data
        }

    def retry_essay_correction(self, essay_id: int, user_id: int, is_admin: bool = False) -> Dict[str, Any]:
        """
        重试作文批改
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID
            is_admin: 是否是管理员，管理员可以重试任何作文
            
        Returns:
            dict: 重试结果
        """
        logger.info(f"开始重试作文批改，作文ID: {essay_id}, 用户ID: {user_id}")
        
        try:
            # 获取作文信息
            essay = Essay.query.get(essay_id)
            if not essay:
                logger.error(f"未找到作文，ID: {essay_id}")
                return {"status": "error", "message": f"未找到作文，ID: {essay_id}"}
            
            # 检查权限，只有作文所有者或管理员可以重试
            if essay.user_id != user_id and not is_admin:
                logger.warning(f"权限不足，用户ID: {user_id}, 作文ID: {essay_id}, 作文所有者ID: {essay.user_id}")
                return {"status": "error", "message": "您没有权限重试此作文"}
            
            # 检查状态，只有失败的作文才能重试
            if essay.status != EssayStatus.FAILED.value:
                if essay.status == EssayStatus.COMPLETED.value:
                    logger.warning(f"作文已完成，无需重试，作文ID: {essay_id}")
                    return {"status": "error", "message": "此作文已成功批改，无需重试"}
                elif essay.status == EssayStatus.CORRECTING.value:
                    logger.warning(f"作文正在批改中，不能重试，作文ID: {essay_id}")
                    return {"status": "error", "message": "此作文正在批改中，请稍后查看结果"}
                else:
                    logger.warning(f"作文状态不允许重试，作文ID: {essay_id}, 状态: {essay.status}")
                    return {"status": "error", "message": f"此作文当前状态不允许重试: {essay.status}"}
            
            # 更新作文状态为待批改
            essay.status = EssayStatus.PENDING.value
            
            # 更新批改记录状态
            correction = Correction.query.filter_by(essay_id=essay_id).first()
            if correction:
                correction.status = 'pending'
                correction.updated_at = datetime.now()
                correction.extra_data = correction.extra_data or {}
                correction.extra_data['retry_count'] = correction.extra_data.get('retry_count', 0) + 1
                correction.extra_data['retry_time'] = datetime.now().isoformat()
                correction.extra_data['retry_by'] = user_id
            else:
                # 如果没有批改记录，创建一个新的
                correction = self._get_or_create_correction(essay_id, 'ai')
            
            # 提交更改
            db.session.commit()
            
            # 创建任务记录
            from app.tasks.correction_tasks import process_essay_correction
            try:
                # 提交到Celery队列
                task = process_essay_correction.delay(essay_id)
                logger.info(f"重试任务已提交，作文ID: {essay_id}, 任务ID: {task.id}")
                
                # 更新任务ID
                correction.task_id = task.id
                db.session.commit()
                
                return {
                    "status": "success",
                    "message": "作文批改任务已重新提交",
                    "essay_id": essay_id,
                    "task_id": task.id
                }
            except Exception as e:
                logger.error(f"提交重试任务失败: {str(e)}")
                essay.status = EssayStatus.FAILED.value
                if correction:
                    correction.status = 'failed'
                    correction.extra_data = correction.extra_data or {}
                    correction.extra_data['retry_error'] = str(e)
                db.session.commit()
                
                return {
                    "status": "error",
                    "message": f"提交重试任务失败: {str(e)}",
                    "essay_id": essay_id
                }
            
        except Exception as e:
            logger.error(f"重试作文批改时发生错误: {str(e)}\n{traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"重试作文批改时发生错误: {str(e)}",
                "essay_id": essay_id
            }

    def _perform_ai_correction(self, essay_content: str) -> Dict[str, Any]:
        """
        执行AI批改逻辑
        
        Args:
            essay_content: 作文内容
            
        Returns:
            Dict: 批改结果
        """
        try:
            logger.info(f"开始批改作文，内容长度: {len(essay_content)} 字符")
            
            # 调用AI批改服务
            correction_results = self.ai_corrector.correct_essay(essay_content)
            
            # 检查AI返回结果的整体状态
            if not isinstance(correction_results, dict):
                logger.error(f"AI批改服务返回无效结果类型: {type(correction_results)}")
                return {
                    "status": "error",
                    "message": "AI批改服务返回无效结果类型"
                }
                
            if correction_results.get("status") != "success":
                error_msg = correction_results.get("message", "AI批改服务返回错误")
                logger.error(f"AI批改服务返回错误: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            # 从AI响应中提取原始数据
            result_data = correction_results.get("result", {})
            
            # 检查result是否为None或非字典
            if result_data is None:
                logger.error("AI批改服务返回结果为None")
                return {
                    "status": "error",
                    "message": "AI批改服务返回结果为None"
                }
            
            # 如果是字符串，尝试解析为JSON
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except json.JSONDecodeError as e:
                    logger.error(f"解析AI返回结果失败: {str(e)}")
                    return {
                        "status": "error",
                        "message": f"解析AI返回结果失败: {str(e)}"
                    }
            
            # 确认result_data是字典类型
            if not isinstance(result_data, dict):
                logger.error(f"AI批改服务返回无效结果格式: {type(result_data)}")
                return {
                    "status": "error",
                    "message": "AI批改服务返回无效结果格式"
                }
            
            # 检查结果中是否包含必要字段
            if not ("总得分" in result_data or "score" in result_data):
                logger.error(f"AI批改服务返回结果缺少必要字段，返回: {result_data}")
                # 如果是调试模式生成的模拟结果，但结构不正确
                if result_data.get("is_mock", False):
                    logger.warning("使用调试模式生成的模拟结果")
                    result_data = self._generate_mock_result()
                else:
                    return {
                        "status": "error",
                        "message": "AI批改服务返回结果缺少必要字段"
                    }
            
            # 构建标准化的返回结果（处理中文字段名称或英文字段名称的情况）
            score = result_data.get("score", result_data.get("总得分", 0))
            if not isinstance(score, (int, float)):
                logger.warning(f"得分格式无效: {score}，设置为默认值0")
                score = 0
                
            # 获取分项得分（处理中文或英文字段）
            subscores = result_data.get("details", result_data.get("分项得分", {}))
            if not isinstance(subscores, dict):
                logger.warning(f"分项得分格式无效: {subscores}，使用空字典")
                subscores = {}
                
            # 处理各种可能的字段名
            content_score = subscores.get("content_score", subscores.get("内容主旨", 0))
            language_score = subscores.get("language_score", subscores.get("语言文采", 0))
            structure_score = subscores.get("structure_score", subscores.get("文章结构", 0))
            writing_score = subscores.get("writing_score", subscores.get("文面书写", 0))
            
            # 处理错误分析（可能是中文字段或英文字段）
            content_analysis = result_data.get("content_analysis", result_data.get("内容分析", ""))
            language_analysis = result_data.get("language_analysis", result_data.get("语言分析", ""))
            structure_analysis = result_data.get("structure_analysis", result_data.get("结构分析", ""))
            spelling_errors = result_data.get("spelling_errors", result_data.get("错别字", []))
            
            # 处理评价和建议（可能是中文字段或英文字段）
            feedback = result_data.get("feedback", result_data.get("总体评价", ""))
            suggestions = result_data.get("improvement_suggestions", result_data.get("写作建议", ""))
            
            # 构建标准化的返回结果
            standardized_result = {
                "score": score,
                "corrected_text": essay_content,  # 由于当前API不返回修改后的文本，暂时使用原文
                "feedback": feedback,
                "error_analysis": json.dumps({
                    "spelling_errors": spelling_errors,
                    "content_analysis": content_analysis,
                    "language_analysis": language_analysis,
                    "structure_analysis": structure_analysis
                }, ensure_ascii=False),
                "improvement_suggestions": suggestions,
                "details": {
                    "content_score": content_score,
                    "language_score": language_score,
                    "structure_score": structure_score,
                    "writing_score": writing_score
                },
                "raw_result": result_data  # 保存原始结果用于调试
            }
            
            logger.info(f"AI批改完成，得分: {standardized_result['score']}")
            
            return {
                "status": "success",
                "data": standardized_result
            }
            
        except Exception as e:
            error_msg = f"执行AI批改失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"错误详情: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": error_msg
            }
            
    def _generate_mock_result(self) -> Dict:
        """
        生成模拟批改结果（用于调试或AI服务返回无效结果时）
        
        Returns:
            Dict: 模拟的批改结果
        """
        # 生成随机分数 (30-50分)
        total_score = random.randint(30, 50)
        
        # 分项得分
        content_score = int(total_score * 0.35)
        language_score = int(total_score * 0.25)
        structure_score = int(total_score * 0.15)
        writing_score = int(total_score * 0.10)
        
        return {
            "总得分": total_score,
            "分项得分": {
                "内容主旨": content_score,
                "语言文采": language_score,
                "文章结构": structure_score,
                "文面书写": writing_score
            },
            "总体评价": "这是一份自动生成的评价。作文内容结构合理，但需要注意错别字和语言表达方面的问题。建议多阅读优秀范文，提高语言表达能力。",
            "内容分析": "文章主题明确，有一定的思想深度。能够围绕主题展开论述，但论据的说服力和创新性有待提高。",
            "语言分析": "语言表达基本流畅，用词基本准确，但部分句式单一，缺乏变化。建议增加修辞手法的运用。",
            "结构分析": "文章结构比较清晰，但过渡不够自然，段落之间的连贯性有待加强。",
            "错别字": [],
            "写作建议": "1. 增加论据的说服力；2. 丰富句式和修辞手法；3. 加强段落间的过渡；4. 注意错别字的修正。",
            "is_mock": True
        } 