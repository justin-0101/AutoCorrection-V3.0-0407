#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery信号处理模块
负责处理Celery任务的各种信号以实现任务状态的自动跟踪
"""

import logging
import json
from celery.signals import task_prerun, task_postrun, task_success, task_failure, task_retry
from app.models.task_status import TaskStatus, TaskState
from app.models.db import db

logger = logging.getLogger(__name__)

@task_prerun.connect
def track_task_started(task_id, task, *args, **kwargs):
    """
    任务开始前创建或更新任务状态记录
    """
    logger.debug(f"[信号处理] 任务启动: {task_id}")
    
    try:
        # 获取相关信息
        task_name = task.name
        
        # 将参数转换为字符串
        args_str = json.dumps(args) if args else None
        kwargs_str = json.dumps(kwargs) if kwargs else None
        
        with db.session() as session:
            # 检查是否已存在记录
            task_status = session.query(TaskStatus).filter_by(task_id=task_id).first()
            
            if task_status:
                # 更新现有记录
                task_status.status = TaskState.RUNNING
                task_status.started_at = db.func.now()
                task_status.worker_id = task.request.hostname if hasattr(task, 'request') else None
                logger.debug(f"[信号处理] 更新任务状态: {task_id}")
            else:
                # 创建新记录
                task_status = TaskStatus(
                    task_id=task_id,
                    task_name=task_name,
                    status=TaskState.RUNNING,
                    args=args_str,
                    kwargs=kwargs_str,
                    worker_id=task.request.hostname if hasattr(task, 'request') else None,
                    started_at=db.func.now()
                )
                session.add(task_status)
                logger.debug(f"[信号处理] 创建任务状态记录: {task_id}")
            
            session.commit()
    except Exception as e:
        logger.error(f"[信号处理] 跟踪任务启动失败: {task_id}, 错误: {str(e)}")


@task_success.connect
def track_task_success(sender, **kwargs):
    """
    任务成功完成时更新任务状态
    """
    if not sender or not sender.request:
        return
    
    task_id = sender.request.id
    logger.debug(f"[信号处理] 任务成功: {task_id}")
    
    try:
        result = sender.request.result
        result_dict = result if isinstance(result, dict) else {'result': result}
        
        with db.session() as session:
            task_status = session.query(TaskStatus).filter_by(task_id=task_id).first()
            
            if task_status:
                task_status.status = TaskState.SUCCESS
                task_status.result = result_dict
                task_status.completed_at = db.func.now()
                session.commit()
                logger.debug(f"[信号处理] 更新任务成功状态: {task_id}")
            else:
                logger.warning(f"[信号处理] 找不到任务记录来更新成功状态: {task_id}")
    except Exception as e:
        logger.error(f"[信号处理] 更新任务成功状态失败: {task_id}, 错误: {str(e)}")


@task_failure.connect
def track_task_failure(sender, task_id, exception, **kwargs):
    """
    任务失败时更新任务状态
    """
    logger.debug(f"[信号处理] 任务失败: {task_id}")
    
    try:
        error_message = str(exception)
        
        with db.session() as session:
            task_status = session.query(TaskStatus).filter_by(task_id=task_id).first()
            
            if task_status:
                task_status.status = TaskState.FAILED
                task_status.error = error_message
                task_status.completed_at = db.func.now()
                session.commit()
                logger.debug(f"[信号处理] 更新任务失败状态: {task_id}")
            else:
                logger.warning(f"[信号处理] 找不到任务记录来更新失败状态: {task_id}")
    except Exception as e:
        logger.error(f"[信号处理] 更新任务失败状态失败: {task_id}, 错误: {str(e)}")


@task_retry.connect
def track_task_retry(sender, request, reason, **kwargs):
    """
    任务重试时更新任务状态
    """
    if not request:
        return
        
    task_id = request.id
    logger.debug(f"[信号处理] 任务重试: {task_id}")
    
    try:
        with db.session() as session:
            task_status = session.query(TaskStatus).filter_by(task_id=task_id).first()
            
            if task_status:
                task_status.status = TaskState.RETRY
                task_status.retry_count = task_status.retry_count + 1
                task_status.error = f"重试原因: {str(reason)}"
                session.commit()
                logger.debug(f"[信号处理] 更新任务重试状态: {task_id}")
            else:
                logger.warning(f"[信号处理] 找不到任务记录来更新重试状态: {task_id}")
    except Exception as e:
        logger.error(f"[信号处理] 更新任务重试状态失败: {task_id}, 错误: {str(e)}")

# 用于显式加载此模块
def register_signal_handlers():
    """
    注册所有信号处理函数
    """
    logger.info("Celery任务状态跟踪信号处理器已注册")
    return True 