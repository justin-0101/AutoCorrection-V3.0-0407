#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery 应用模块
用于初始化和配置 Celery 应用
"""

import os
import logging
from celery import Celery
from flask import Flask, current_app
# 移除从app导入create_app

# 创建日志记录器
logger = logging.getLogger(__name__)

def create_celery_app(app: Flask = None) -> Celery:
    """
    创建 Celery 应用实例
    
    Args:
        app: Flask应用实例，可选
        
    Returns:
        Celery: Celery应用实例
    """
    # 如果没有提供 Flask 应用，创建一个简单的Celery实例
    # 避免循环导入，不再直接创建Flask应用
    if not app:
        # 创建一个简单的Celery实例，使用环境变量中的配置
        broker = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0') 
        celery = Celery('app', broker=broker, backend=backend)
        
        # 配置Celery
        celery.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='Asia/Shanghai',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,  # 1小时
            worker_max_tasks_per_child=200,
            worker_prefetch_multiplier=1
        )
        logger.info("使用简单配置创建Celery实例")
        return celery
    
    # 使用提供的Flask应用创建Celery应用
    try:
        celery = Celery(
            app.import_name,
            broker=app.config['CELERY_BROKER_URL'],
            backend=app.config['CELERY_RESULT_BACKEND']
        )
        
        # 更新 Celery 配置
        celery.conf.update(app.config)
        
        # 设置任务序列化格式
        celery.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='Asia/Shanghai',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,  # 1小时
            worker_max_tasks_per_child=200,
            worker_prefetch_multiplier=1
        )
        
        # 添加错误处理
        from celery.signals import task_failure
        @task_failure.connect
        def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo, **_):
            logger.error(
                f"任务失败 [task_id={task_id}]: {str(exception)}\n"
                f"参数: args={args}, kwargs={kwargs}\n"
                f"错误详情:\n{einfo}"
            )
        
        class ContextTask(celery.Task):
            """确保任务在应用上下文中运行"""
            abstract = True
            
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return super().__call__(*args, **kwargs)
            
            def on_failure(self, exc, task_id, args, kwargs, einfo):
                """任务失败时的处理"""
                with app.app_context():
                    logger.error(
                        f"任务执行失败 [task_id={task_id}]: {str(exc)}\n"
                        f"参数: args={args}, kwargs={kwargs}\n"
                        f"错误详情:\n{einfo}"
                    )
                    super().on_failure(exc, task_id, args, kwargs, einfo)
            
            def on_retry(self, exc, task_id, args, kwargs, einfo):
                """任务重试时的处理"""
                with app.app_context():
                    logger.warning(
                        f"任务重试 [task_id={task_id}]: {str(exc)}\n"
                        f"参数: args={args}, kwargs={kwargs}"
                    )
                    super().on_retry(exc, task_id, args, kwargs, einfo)
            
            def after_return(self, status, retval, task_id, args, kwargs, einfo):
                """任务完成后的处理"""
                with app.app_context():
                    if status == 'SUCCESS':
                        logger.info(
                            f"任务完成 [task_id={task_id}]\n"
                            f"参数: args={args}, kwargs={kwargs}\n"
                            f"返回值: {retval}"
                        )
                    super().after_return(status, retval, task_id, args, kwargs, einfo)
        
        # 设置默认任务基类
        celery.Task = ContextTask
        logger.info("使用Flask应用上下文创建Celery实例")
        return celery
    
    except Exception as e:
        logger.error(f"创建Celery应用时出错: {str(e)}")
        raise

# 使用简单配置创建Celery实例，避免循环导入
celery = create_celery_app() 