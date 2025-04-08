#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改流程控制器
处理作文批改的完整工作流程，包括接收作文、预处理、AI批改和结果处理
"""

import os
import logging
import threading
import time
import json
from typing import Dict, Any, Optional, Callable, Tuple, List
from datetime import datetime

from core.essay_model import Essay
from core.user_model import User
from core.ai_corrector import AICorrectionService, AIServiceError
from utils.exceptions import ValidationError, DatabaseError, db_error_handler
from config.app_config import APP_CONFIG

# 配置日志记录器
logger = logging.getLogger('autocorrection.controller')

class CorrectionController:
    """
    作文批改控制器类
    
    负责协调作文批改的完整流程，包括:
    1. 输入验证和预处理
    2. 调用AI批改服务
    3. 处理和保存批改结果
    4. 处理异常情况
    """
    
    def __init__(self):
        """初始化批改控制器"""
        self.ai_service = AICorrectionService()
        self.active_tasks = {}  # 跟踪活跃的批改任务
        self.lock = threading.Lock()  # 用于同步访问活跃任务列表
    
    def submit_correction(self, user_id: int, title: str, content: str, 
                         grade: str, callback: Optional[Callable] = None) -> Tuple[bool, str, int]:
        """
        提交作文进行批改
        
        Args:
            user_id: 用户ID
            title: 作文标题
            content: 作文内容
            grade: 作文年级水平 (primary, junior, senior, college)
            callback: 可选的回调函数，当批改完成时调用
            
        Returns:
            Tuple[bool, str, int]: (成功标志, 消息, 作文ID)
        """
        try:
            # 验证输入
            self._validate_correction_input(user_id, title, content, grade)
            
            # 验证用户作文数量限制
            user = User.find_by_id(user_id)
            if not user:
                raise ValidationError(f"用户ID {user_id} 不存在")
            
            can_submit, message = user.check_essay_limit()
            if not can_submit:
                logger.warning(f"用户 {user_id} 超出作文提交限制: {message}")
                return False, message, 0
            
            # 创建作文记录
            essay = Essay(
                user_id=user_id,
                title=title,
                content=content,
                grade=grade,
                status='pending',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            essay_id = essay.save()
            
            # 启动异步批改任务
            self._start_correction_task(essay, callback)
            
            logger.info(f"作文提交成功，ID: {essay_id}，用户ID: {user_id}")
            return True, "作文提交成功，正在批改中", essay_id
            
        except ValidationError as e:
            logger.warning(f"作文提交验证失败: {str(e)}")
            return False, str(e), 0
        except Exception as e:
            logger.error(f"作文提交异常: {str(e)}", exc_info=True)
            return False, f"提交失败: {str(e)}", 0
    
    def get_correction_status(self, essay_id: int) -> Dict[str, Any]:
        """
        获取作文批改状态
        
        Args:
            essay_id: 作文ID
            
        Returns:
            Dict: 包含作文批改状态的字典
        """
        try:
            essay = Essay.find_by_id(essay_id)
            if not essay:
                return {
                    "success": False,
                    "message": f"作文ID {essay_id} 不存在",
                    "status": "not_found"
                }
            
            # 检查是否在活跃任务中
            with self.lock:
                is_active = essay_id in self.active_tasks
            
            return {
                "success": True,
                "essay_id": essay.id,
                "title": essay.title,
                "status": essay.status,
                "is_active": is_active,
                "score": essay.score,
                "created_at": essay.created_at.isoformat() if isinstance(essay.created_at, datetime) else essay.created_at,
                "updated_at": essay.updated_at.isoformat() if isinstance(essay.updated_at, datetime) else essay.updated_at
            }
        except Exception as e:
            logger.error(f"获取批改状态异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"获取状态失败: {str(e)}",
                "status": "error"
            }
    
    def list_user_corrections(self, user_id: int, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        获取用户的作文批改列表
        
        Args:
            user_id: 用户ID
            limit: 每页数量限制
            offset: 分页偏移量
            
        Returns:
            Dict: 包含用户作文列表的字典
        """
        try:
            essays = Essay.find_by_user_id(user_id, limit, offset)
            total_count = Essay.count_by_user_id(user_id)
            
            essays_data = [essay.to_dict(include_content=False) for essay in essays]
            
            return {
                "success": True,
                "essays": essays_data,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"获取用户作文列表异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"获取作文列表失败: {str(e)}",
                "essays": []
            }
    
    def get_correction_result(self, essay_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取作文批改结果
        
        Args:
            essay_id: 作文ID
            user_id: 可选的用户ID，用于验证作文所有权
            
        Returns:
            Dict: 包含完整批改结果的字典
        """
        try:
            # 查找作文
            essay = Essay.find_by_id(essay_id, with_content=True)
            if not essay:
                return {
                    "success": False,
                    "message": f"作文ID {essay_id} 不存在"
                }
            
            # 验证所有权（如果提供了用户ID）
            if user_id and essay.user_id != user_id:
                logger.warning(f"用户 {user_id} 尝试访问非其所有的作文 {essay_id}")
                return {
                    "success": False,
                    "message": "无权访问此作文"
                }
            
            # 检查批改状态
            if essay.status == 'pending' or essay.status == 'processing':
                return {
                    "success": True,
                    "status": essay.status,
                    "message": "作文正在批改中，请稍后查看结果"
                }
            elif essay.status == 'error':
                return {
                    "success": False,
                    "status": "error",
                    "message": "作文批改失败，请重新提交"
                }
            
            # 解析反馈信息
            feedback = {}
            if essay.feedback:
                try:
                    feedback = json.loads(essay.feedback)
                except json.JSONDecodeError:
                    feedback = {"总体评价": essay.feedback}
            
            # 构建结果
            result = {
                "success": True,
                "essay_id": essay.id,
                "title": essay.title,
                "content": essay.content,
                "grade": essay.grade,
                "word_count": len(essay.content),
                "score": essay.score,
                "status": essay.status,
                "feedback": feedback,
                "created_at": essay.created_at.isoformat() if isinstance(essay.created_at, datetime) else essay.created_at,
                "updated_at": essay.updated_at.isoformat() if isinstance(essay.updated_at, datetime) else essay.updated_at
            }
            
            # 添加分项得分（如果有）
            if hasattr(essay, 'content_score') and essay.content_score is not None:
                result['content_score'] = essay.content_score
            if hasattr(essay, 'language_score') and essay.language_score is not None:
                result['language_score'] = essay.language_score
            if hasattr(essay, 'structure_score') and essay.structure_score is not None:
                result['structure_score'] = essay.structure_score
            if hasattr(essay, 'writing_score') and essay.writing_score is not None:
                result['writing_score'] = essay.writing_score
                
            return result
            
        except Exception as e:
            logger.error(f"获取批改结果异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"获取批改结果失败: {str(e)}"
            }
    
    def _validate_correction_input(self, user_id: int, title: str, content: str, grade: str) -> None:
        """
        验证作文批改输入
        
        Args:
            user_id: 用户ID
            title: 作文标题
            content: 作文内容
            grade: 作文年级水平
            
        Raises:
            ValidationError: 如果输入验证失败
        """
        if not user_id or not isinstance(user_id, int):
            raise ValidationError("用户ID无效")
        
        if not content or len(content.strip()) < 50:
            raise ValidationError("作文内容太短，至少需要50个字符")
        
        if len(content) > 10000:
            raise ValidationError("作文内容太长，不能超过10000个字符")
            
        valid_grades = ['primary', 'junior', 'senior', 'college']
        if grade not in valid_grades:
            raise ValidationError(f"无效的年级类型，可选值为: {', '.join(valid_grades)}")
    
    def _start_correction_task(self, essay: Essay, callback: Optional[Callable] = None) -> None:
        """
        启动异步批改任务
        
        Args:
            essay: 要批改的作文对象
            callback: 可选的回调函数，当批改完成时调用
        """
        # 更新作文状态为处理中
        essay.status = 'processing'
        essay.save()
        
        # 注册活跃任务
        with self.lock:
            self.active_tasks[essay.id] = time.time()
        
        # 开始异步批改线程
        correction_thread = threading.Thread(
            target=self._process_correction,
            args=(essay, callback)
        )
        correction_thread.daemon = True
        correction_thread.start()
        
        logger.info(f"批改任务已启动，作文ID: {essay.id}")
    
    def _process_correction(self, essay: Essay, callback: Optional[Callable] = None) -> None:
        """
        处理作文批改任务
        
        Args:
            essay: 要批改的作文对象
            callback: 可选的回调函数，当批改完成时调用
        """
        essay_id = essay.id
        start_time = time.time()
        
        try:
            logger.info(f"开始批改作文，ID: {essay_id}")
            
            # 调用AI批改服务
            correction_result = self.ai_service.correct_essay(
                content=essay.content,
                grade=essay.grade,
                title=essay.title
            )
            
            # 提取结果
            essay.score = correction_result.get('score', 0)
            essay.feedback = correction_result.get('feedback', '')
            
            # 更新分项得分（如果在模型中定义了这些字段）
            if hasattr(essay, 'content_score') and 'content_score' in correction_result:
                essay.content_score = correction_result['content_score']
            if hasattr(essay, 'language_score') and 'language_score' in correction_result:
                essay.language_score = correction_result['language_score']
            if hasattr(essay, 'structure_score') and 'structure_score' in correction_result:
                essay.structure_score = correction_result['structure_score']
            if hasattr(essay, 'writing_score') and 'writing_score' in correction_result:
                essay.writing_score = correction_result['writing_score']
            
            # 更新作文状态为完成
            essay.status = 'completed'
            essay.updated_at = datetime.now()
            essay.save()
            
            elapsed_time = time.time() - start_time
            logger.info(f"作文批改完成，ID: {essay_id}，耗时: {elapsed_time:.2f}秒，分数: {essay.score}")
            
        except AIServiceError as e:
            # AI服务错误处理
            logger.error(f"AI批改服务错误，作文ID: {essay_id}: {str(e)}")
            essay.status = 'error'
            essay.feedback = f"批改出错: {str(e)}"
            essay.updated_at = datetime.now()
            essay.save()
            
        except Exception as e:
            # 其他未预期错误处理
            logger.error(f"作文批改异常，作文ID: {essay_id}: {str(e)}", exc_info=True)
            essay.status = 'error'
            essay.feedback = "系统错误，请联系管理员"
            essay.updated_at = datetime.now()
            essay.save()
            
        finally:
            # 从活跃任务中移除
            with self.lock:
                if essay_id in self.active_tasks:
                    del self.active_tasks[essay_id]
            
            # 调用回调函数（如果有）
            if callback:
                try:
                    callback(essay)
                except Exception as callback_error:
                    logger.error(f"回调函数执行错误: {str(callback_error)}", exc_info=True)

# 创建单例实例
correction_controller = CorrectionController() 