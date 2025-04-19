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
        
        class ContextTask(celery.Task):
            """确保任务在应用上下文中运行"""
            abstract = True
            
            def __call__(self, *args, **kwargs):
                # 正确检查是否在应用上下文中
                from flask import has_app_context
                if has_app_context():
                    return super().__call__(*args, **kwargs)
                    
                # 否则创建新的应用上下文
                from app import create_app
                app = create_app()
                with app.app_context():
                    # 确保数据库初始化
                    from app.extensions import db
                    if not db.get_engine(app, bind=None):
                        db.init_app(app)
                    return super().__call__(*args, **kwargs)
        
        # 设置默认任务基类
        celery.Task = ContextTask
        logger.info("使用Flask应用上下文创建Celery实例")
        return celery
    
    except Exception as e:
        logger.error(f"创建Celery应用时出错: {str(e)}")
        raise

# 使用简单配置创建Celery实例
celery_app = create_celery_app() 