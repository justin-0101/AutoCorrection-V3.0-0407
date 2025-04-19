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
from app import create_app

logger = logging.getLogger(__name__)

def ensure_app_context(func):
    """确保在Flask应用上下文中执行函数"""
    def wrapper(*args, **kwargs):
        app = create_app()
        with app.app_context():
            return func(*args, **kwargs)
    return wrapper

@task_prerun.connect
@ensure_app_context
def track_task_started(task_id, task, *args, **kwargs):
    """
    任务开始前创建或更新任务状态记录
    """
    logger.debug(f"[信号处理] 任务启动: {task_id}")
    
    try:
        # 获取相关信息
        task_name = task.name
        
        # 将参数转换为字符串，过滤掉不可序列化的对象
        def safe_serializable(obj):
            """返回可以安全序列化为JSON的对象"""
            try:
                # 特殊类型处理
                if hasattr(obj, '__dict__'):
                    return str(obj)
                
                if isinstance(obj, (str, int, float, bool)) or obj is None:
                    return obj
                elif isinstance(obj, (list, tuple)):
                    return [safe_serializable(i) for i in obj]
                elif isinstance(obj, dict):
                    return {k: safe_serializable(v) for k, v in obj.items() 
                            if isinstance(k, str)}  # 只处理键是字符串的项
                return str(obj)  # 将其他类型转换为字符串表示
            except Exception:
                return str(obj)  # 任何异常都返回字符串表示
        
        # 安全地序列化参数，过滤掉信号参数
        filtered_kwargs = {k: v for k, v in kwargs.items() 
                         if not k.startswith('signal') and k != 'sender'}
        
        safe_args = [safe_serializable(arg) for arg in args] if args else []
        safe_kwargs = {k: safe_serializable(v) for k, v in filtered_kwargs.items()} if filtered_kwargs else {}
        
        try:
            args_str = json.dumps(safe_args) if safe_args else None
            kwargs_str = json.dumps(safe_kwargs) if safe_kwargs else None
        except TypeError as e:
            logger.warning(f"参数序列化失败，使用简化表示: {str(e)}")
            args_str = str(args) if args else None
            kwargs_str = str(filtered_kwargs) if filtered_kwargs else None
        
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
@ensure_app_context
def track_task_success(sender, **kwargs):
    """
    任务成功完成时更新任务状态
    """
    if not sender or not hasattr(sender, 'request') or not sender.request:
        logger.warning("[信号处理] 任务成功处理缺少sender或request")
        return
    
    task_id = sender.request.id
    logger.debug(f"[信号处理] 任务成功: {task_id}")
    
    try:
        # 从kwargs中获取结果
        result = kwargs.get('result', None)
        
        # 确保结果可序列化
        result_dict = {}
        if result is not None:
            if isinstance(result, dict):
                # 如果是字典，确保所有值都可序列化
                try:
                    result_dict = {k: v for k, v in result.items() if k != 'sender'}
                    # 测试序列化
                    json.dumps(result_dict)
                except (TypeError, ValueError):
                    # 如果序列化失败，则使用字符串表示
                    result_dict = {'result': str(result)}
            else:
                # 非字典类型，尝试序列化
                try:
                    # 测试是否可序列化
                    json.dumps({'result': result})
                    result_dict = {'result': result}
                except (TypeError, ValueError):
                    # 不可序列化，转为字符串
                    result_dict = {'result': str(result)}
        
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
@ensure_app_context
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
@ensure_app_context
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