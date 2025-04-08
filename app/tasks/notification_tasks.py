#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知任务模块
负责处理任务失败通知和其他系统通知的异步任务
"""

import logging
import traceback
import json
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.core.notification.notification_service import NotificationService
from app.tasks.logging_config import get_task_logger
from app.models.task_status import TaskStatus, TaskState
from app.models.user import User
from app.models.db import db

# 获取任务专用日志记录器
logger = get_task_logger()
notification_service = NotificationService()

@celery_app.task(
    name='app.tasks.notification_tasks.send_task_failure_notification',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='email'
)
def send_task_failure_notification(self, task_id, related_type=None, related_id=None, error_message=None):
    """
    发送任务失败通知
    
    Args:
        self: Celery任务实例
        task_id: 失败任务的ID
        related_type: 关联对象类型
        related_id: 关联对象ID
        error_message: 错误消息
        
    Returns:
        Dict: 处理结果
    """
    logger.info(f"开始发送任务失败通知，任务ID: {task_id}")
    
    try:
        # 获取任务状态记录
        task_status = TaskStatus.find_by_task_id(task_id)
        if not task_status:
            logger.warning(f"任务状态记录未找到，任务ID: {task_id}")
            return {
                'status': 'error',
                'message': '任务状态记录未找到'
            }
        
        # 如果参数中没有提供，则使用任务状态记录中的值
        if not related_type:
            related_type = task_status.related_type
        
        if not related_id:
            related_id = task_status.related_id
            
        if not error_message and task_status.error_message:
            error_message = task_status.error_message
        elif not error_message:
            error_message = "未知错误"
        
        # 获取相关用户ID
        user_id = None
        if related_type == 'essay' and related_id:
            try:
                from app.models.essay import Essay
                essay = Essay.query.get(related_id)
                if essay:
                    user_id = essay.user_id
            except Exception as e:
                logger.error(f"获取作文相关用户信息失败: {str(e)}")
        
        # 获取管理员用户列表
        admin_users = User.query.filter_by(is_admin=True).all()
        admin_ids = [admin.id for admin in admin_users]
        
        # 准备通知内容
        title = f"任务执行失败: {task_status.task_name}"
        content = f"""
        系统检测到一个任务执行失败。

        任务ID: {task_id}
        任务名称: {task_status.task_name}
        关联对象: {related_type} ({related_id if related_id else 'N/A'})
        重试次数: {task_status.retry_count}/{task_status.max_retries}
        错误信息: {error_message}
        失败时间: {task_status.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task_status.completed_at else datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # 创建上下文数据
        context_data = {
            'task_id': task_id,
            'task_name': task_status.task_name,
            'related_type': related_type,
            'related_id': related_id,
            'error_message': error_message,
            'retry_count': task_status.retry_count,
            'max_retries': task_status.max_retries
        }
        
        # 向管理员发送系统通知
        for admin_id in admin_ids:
            notification_result = notification_service.send_notification(
                user_id=admin_id,
                title=title,
                content=content,
                notification_type='task_failure',
                context_data=context_data
            )
            logger.info(f"管理员通知发送结果: {notification_result}")
        
        # 如果与用户相关，也向用户发送通知
        if user_id:
            # 创建更友好的用户通知
            user_title = "您的任务处理出现问题"
            user_content = f"""
            我们在处理您的{get_readable_related_type(related_type)}时遇到了一些技术问题。
            
            我们的技术团队已经收到通知，并将尽快解决。
            
            如果问题持续，请联系客服获取帮助。
            
            错误参考号: {task_id[-8:]}
            """
            
            user_notification_result = notification_service.send_notification(
                user_id=user_id,
                title=user_title,
                content=user_content,
                notification_type='task_failure',
                context_data=context_data
            )
            logger.info(f"用户通知发送结果: {user_notification_result}")
        
        return {
            'status': 'success',
            'message': '任务失败通知已发送',
            'admin_notified': len(admin_ids),
            'user_notified': 1 if user_id else 0
        }
        
    except Exception as e:
        logger.error(f"发送任务失败通知时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 判断是否应该重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 {self.default_retry_delay} 秒后重试发送任务失败通知")
            self.retry(exc=e, countdown=self.default_retry_delay)
        
        return {
            'status': 'error',
            'message': f'发送通知失败: {str(e)}'
        }

def get_readable_related_type(related_type):
    """
    获取关联对象类型的可读名称
    
    Args:
        related_type: 关联对象类型
        
    Returns:
        str: 可读名称
    """
    type_mapping = {
        'essay': '作文批改',
        'payment': '支付处理',
        'subscription': '会员订阅',
        'backup': '备份任务',
        'user': '账户操作',
        'email': '邮件发送'
    }
    
    return type_mapping.get(related_type, '系统任务')

@celery_app.task(
    name='app.tasks.notification_tasks.process_failed_tasks_notification',
    bind=True,
    max_retries=2,
    queue='periodic'
)
def process_failed_tasks_notification(self):
    """
    定期处理失败任务通知
    查找最近失败的任务并发送通知
    
    Args:
        self: Celery任务实例
        
    Returns:
        Dict: 处理结果
    """
    logger.info("开始处理定期失败任务通知")
    
    try:
        # 查找最近30分钟内失败的任务
        from datetime import timedelta
        time_threshold = datetime.utcnow() - timedelta(minutes=30)
        
        # 查询失败状态且尚未发送通知的任务
        failed_tasks = db.session.query(TaskStatus).filter(
            TaskStatus.status == TaskState.FAILURE,
            TaskStatus.completed_at >= time_threshold,
            TaskStatus.options.notlike('%"notification_sent": true%')
        ).all()
        
        logger.info(f"找到 {len(failed_tasks)} 个需要发送通知的失败任务")
        
        notification_sent_count = 0
        for task in failed_tasks:
            try:
                # 发送任务失败通知
                send_task_failure_notification.delay(
                    task.task_id,
                    task.related_type,
                    task.related_id,
                    task.error_message
                )
                
                # 更新任务选项，标记为已发送通知
                task.options = task.options or {}
                if isinstance(task.options, str):
                    try:
                        task.options = json.loads(task.options)
                    except:
                        task.options = {}
                
                task.options['notification_sent'] = True
                task.options['notification_time'] = datetime.utcnow().isoformat()
                
                # 提交更改
                db.session.commit()
                notification_sent_count += 1
                
            except Exception as task_error:
                logger.error(f"处理任务 {task.task_id} 的失败通知时出错: {str(task_error)}")
                db.session.rollback()
        
        return {
            'status': 'success',
            'message': f'已为 {notification_sent_count}/{len(failed_tasks)} 个失败任务发送通知'
        }
        
    except Exception as e:
        logger.error(f"处理定期失败任务通知时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 判断是否应该重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 60 秒后重试处理定期失败任务通知")
            self.retry(exc=e, countdown=60)
        
        return {
            'status': 'error',
            'message': f'处理失败任务通知失败: {str(e)}'
        } 