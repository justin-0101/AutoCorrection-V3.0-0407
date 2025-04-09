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
from typing import Dict, Any, List, Optional, Union
import uuid
import traceback
import re
import time

from sqlalchemy.exc import SQLAlchemyError
from app.config import config
from app.utils import FileHandler
from app.core.user.user_service import UserService
from app.models.essay import Essay, EssayStatus
from app.models.user import User, MembershipLevel
from app.models.db import db
from app.models.correction import Correction
from app.core.correction.ai_corrector import AICorrectionService
from app.core.ai.open_ai_client import OpenAIClient
from app.core.correction.report_generator import ReportGenerator
from app.extensions import db
from app.utils.exceptions import (
    ResourceNotFoundError, ValidationError, 
    LimitExceededError, ServiceUnavailableError
)

logger = logging.getLogger(__name__)

class CorrectionService:
    """作文批改服务类"""
    
    def __init__(self):
        """初始化批改服务"""
        self.file_handler = FileHandler()
        self.user_service = UserService()
        self.ai_corrector = AICorrectionService()
        self.report_generator = ReportGenerator()
        
        # 配置选项
        self.essay_limits = config.MEMBERSHIP_CONFIG.get('essay_limits', {
            MembershipLevel.FREE.value: {'daily': 1, 'monthly': 5},
            MembershipLevel.BASIC.value: {'daily': 3, 'monthly': 30},
            MembershipLevel.PREMIUM.value: {'daily': 10, 'monthly': 100}
        })
        
        # 批改的作文最大长度
        self.max_essay_length = config.APP_CONFIG.get('max_essay_length', 5000)
        
        # 支持的文件类型
        self.supported_extensions = config.APP_CONFIG.get('allowed_extensions', {
            'text': ['txt', 'docx', 'pdf'],
            'image': ['jpg', 'jpeg', 'png']
        })
        
        # 允许的最大作文长度
        self.max_content_length = 5000
        
        # 默认批改评分项
        self.default_scoring_items = [
            '内容', '语言', '结构', '书写'
        ]
        
        logger.info("批改服务已初始化")
    
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
                'updated_at': datetime.datetime.now()
            }
            
            # 只保留Essay模型中实际存在的字段
            valid_params = {k:v for k,v in create_params.items() if hasattr(Essay, k)}
            
            # 创建Essay对象
            essay = Essay(**valid_params)
            db.session.add(essay)
            db.session.commit()
            
            # 启动异步批改任务
            from app.tasks.correction_tasks import process_essay_correction
            task = process_essay_correction.delay(essay.id)
            
            # 返回结果
            return {
                'status': 'success',
                'message': '作文已提交并开始批改',
                'essay_id': essay.id,
                'task_id': task.id
            }
            
        except Exception as e:
            logger.error(f"提交作文时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
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
                source_type=file_result['source_type'],
                file_path=file_result['path'],
                file_name=file_result['original_filename']
            )
            
            db.session.add(essay)
            db.session.commit()
            
            # 异步处理批改任务
            process_essay_correction.delay(essay.id)
            
            # 返回结果
            result = self._create_success_result(essay, None)
            
            # 记录提交成功
            logger.info(f"用户 {user_id} 以API方式提交作文成功，ID: {essay.id}")
            
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
                'content': essay.content,
                'status': essay.status,
                'source_type': essay.source_type,
                'file_name': essay.file_name,
                'user_id': essay.user_id,
                'created_at': essay.created_at.isoformat() if essay.created_at else None,
                'updated_at': essay.updated_at.isoformat() if essay.updated_at else None
            }
            
            # 如果已批改完成，添加批改结果
            if essay.status == EssayStatus.COMPLETED.value and essay.correction_result:
                essay_data['correction_result'] = essay.correction_result
            
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
                    'file_name': essay.file_name,
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
            if essay.file_path and os.path.exists(essay.file_path):
                self.file_handler.delete_file(essay.file_path)
            
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
    
    def perform_correction(self, essay_id):
        """
        执行作文批改
        
        Args:
            essay_id: 作文ID
            
        Returns:
            dict: 批改结果
        """
        logger.info(f"开始批改作文 {essay_id}")
        
        # 获取作文
        try:
            essay = Essay.query.get(essay_id)
            if not essay:
                logger.error(f"找不到作文: {essay_id}")
                return {
                    'status': 'error',
                    'message': f"找不到作文: {essay_id}"
                }
                
            logger.info(f"成功获取作文，标题: {essay.title}, 作者: {essay.user_id}, 长度: {len(essay.content or '')}")
            
            # 删除记录
            try:
                # 更新作文状态
                essay.status = EssayStatus.CORRECTING.value
                db.session.commit()
                
                # 检查是否已有批改记录
                correction = Correction.query.filter_by(essay_id=essay_id).first()
                
                # 如果没有批改记录，创建一个新的
                if not correction:
                    correction = Correction(
                        essay_id=essay_id,
                        type='ai',
                        status='processing'  # 设置初始状态为processing
                    )
                    db.session.add(correction)
                    db.session.commit()
                else:
                    # 更新现有批改记录的状态
                    correction.status = 'processing'
                    db.session.commit()
                
                # 调用AI服务前记录
                logger.info(f"准备调用AI服务批改作文 {essay_id}")
                logger.debug(f"AI批改输入: 标题={essay.title}, 内容长度={len(essay.content or '')}")
                
                # 获取AI服务客户端
                ai_client = self.ai_corrector
                if not ai_client:
                    logger.error("无法获取AI客户端")
                    return {
                        'status': 'error',
                        'message': "无法获取AI客户端"
                    }
                    
                logger.info(f"已获取AI客户端: {type(ai_client).__name__}")
                
                # 调用AI服务进行批改
                try:
                    start_time = time.time()
                    logger.info(f"开始AI批改，作文ID: {essay_id}")
                    result = ai_client.correct_essay(
                        content=essay.content
                    )
                    elapsed_time = time.time() - start_time
                    logger.info(f"AI批改完成，耗时: {elapsed_time:.2f}秒，结果大小: {len(str(result))}")
                    logger.debug(f"AI批改结果包含字段: {', '.join(result.keys() if isinstance(result, dict) else [])}")
                    
                    # 提取AI批改回复中的关键信息
                    if isinstance(result, dict):
                        if 'scores' in result:
                            logger.info(f"批改得分: 总分={result['scores'].get('total_score', '未知')}, 内容={result['scores'].get('content_score', '未知')}, 语言={result['scores'].get('language_score', '未知')}")
                        else:
                            logger.warning("AI批改结果中未包含分数信息")
                    else:
                        logger.warning(f"AI批改结果格式异常: {type(result)}")
                        
                    # 仅当API返回成功时更新批改记录
                    if result["status"] == "success" and result.get("result"):
                        result_data = result["result"]
                        
                        # 更新批改记录
                        correction.score = result_data.get('总得分', 0)
                        correction.content = json.dumps(result_data)
                        correction.comments = result_data.get('总体评价', '')
                        correction.error_analysis = json.dumps(result_data.get('错别字', []))
                        correction.improvement_suggestions = result_data.get('improvement_suggestions', '')
                        correction.extra_data = result_data
                        correction.status = 'completed'  # 更新状态为completed
                        correction.results = json.dumps(result_data)  # 存储完整结果
                        
                        # 更新作文状态
                        essay.status = EssayStatus.COMPLETED.value
                        
                        db.session.commit()
                        logger.info(f"批改完成，作文ID: {essay_id}")
                        
                        return {
                            "status": "success",
                            "essay_id": essay_id,
                            "correction_id": correction.id,
                            "results": result_data
                        }
                    else:
                        error_msg = result.get("message", "AI批改返回无效结果")
                        logger.error(f"AI批改失败，作文ID: {essay_id}, 错误: {error_msg}")
                        
                        # 更新批改记录和作文状态为失败
                        correction.status = 'failed'  # 更新状态为failed
                        essay.status = EssayStatus.FAILED.value  # 标记为失败
                        
                        correction.extra_data = correction.extra_data or {}
                        correction.extra_data['error'] = error_msg
                        
                        db.session.commit()
                        
                        return {
                            "status": "error",
                            "message": f"AI批改失败: {error_msg}",
                            "essay_id": essay_id
                        }
                        
                except Exception as e:
                    logger.error(f"批改过程中发生错误，作文ID: {essay_id}, 错误: {str(e)}")
                    
                    # 更新批改记录和作文状态为失败
                    correction.status = 'failed'  # 更新状态为failed
                    essay.status = EssayStatus.FAILED.value  # 标记为失败
                    
                    correction.extra_data = correction.extra_data or {}
                    correction.extra_data['error'] = str(e)
                    
                    db.session.commit()
                    
                    return {
                        "status": "error",
                        "message": f"批改过程中发生错误: {str(e)}",
                        "essay_id": essay_id
                    }
                
            except Exception as e:
                logger.error(f"批改过程中发生错误，作文ID: {essay_id}, 错误: {str(e)}")
                return {
                    "status": "error",
                    "message": f"批改过程中发生错误: {str(e)}",
                    "essay_id": essay_id
                }
                
        except Exception as e:
            logger.error(f"批改过程中发生错误，作文ID: {essay_id}, 错误: {str(e)}")
            return {
                "status": "error",
                "message": f"批改过程中发生错误: {str(e)}",
                "essay_id": essay_id
            }
    
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

    def _create_success_result(self, essay, correction):
        # 构造返回结果
        essay_data = {
            'id': essay.id,
            'title': essay.title,
            'content': essay.content,
            'status': essay.status,
            'source_type': essay.source_type,
            'file_name': essay.file_name,
            'user_id': essay.user_id,
            'created_at': essay.created_at.isoformat() if essay.created_at else None,
            'updated_at': essay.updated_at.isoformat() if essay.updated_at else None
        }
        
        # 如果已批改完成，添加批改结果
        if essay.status == EssayStatus.COMPLETED.value and essay.correction_result:
            essay_data['correction_result'] = essay.correction_result
        
        # 如果已批改完成，添加批改记录
        if correction:
            essay_data['correction_id'] = correction.id
            essay_data['correction_score'] = correction.score
            essay_data['correction_content'] = correction.content
            essay_data['correction_comments'] = correction.comments
            essay_data['correction_error_analysis'] = correction.error_analysis
            essay_data['correction_improvement_suggestions'] = correction.improvement_suggestions
            essay_data['correction_extra_data'] = correction.extra_data
            essay_data['correction_status'] = correction.status
            essay_data['correction_results'] = correction.results
        
        return {
            'status': 'success',
            'essay': essay_data
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
                correction = Correction(
                    essay_id=essay_id,
                    type='ai',
                    status='pending'
                )
                db.session.add(correction)
            
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