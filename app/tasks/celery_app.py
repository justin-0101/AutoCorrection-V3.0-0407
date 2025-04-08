#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery应用配置模块
为应用提供异步任务处理能力
"""

import os
import logging
from celery import Celery
from celery.signals import worker_process_init, worker_ready, worker_process_shutdown, task_prerun, task_postrun
from app.config import Config

def create_celery_app():
    """
    创建Celery应用实例
    """
    celery = Celery(
        'app',
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND,
        include=['app.tasks']
    )

    # 配置Celery
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True,
    )

    return celery

celery_app = create_celery_app()

logger = logging.getLogger(__name__)

# 全局应用实例，确保在进程间共享
flask_app = None

@worker_process_init.connect
def init_worker_process(sender, **kwargs):
    """
    Celery工作进程初始化时执行
    初始化数据库连接和服务
    """
    global flask_app
    
    logger.info("初始化Celery工作进程...")
    try:
        # 导入Flask应用工厂函数
        from app import create_app
        
        # 创建Flask应用实例
        flask_app = create_app()
        
        if not flask_app:
            logger.error("无法创建Flask应用实例")
            return
            
        logger.info("已成功创建Flask应用实例")
        
        # 推送应用上下文 - 测试应用上下文是否可以创建
        with flask_app.app_context():
            logger.info("Flask应用上下文测试成功")
            logger.info("应用上下文管理工作正常")
            
            # 初始化必要的服务
            try:
                from app.core.ai.init_services import ensure_services
                if ensure_services():
                    logger.info("服务初始化成功")
                else:
                    logger.error("服务初始化失败")
            except Exception as e:
                logger.error(f"初始化服务时出错: {str(e)}")
                
            # 设置数据库连接池配置
            try:
                from app.extensions import db
                
                # 确保每个工作进程有自己的连接池
                logger.info("配置数据库连接池")
                db.engine.dispose()
                
                # 重新配置连接池
                db.engine.pool_size = 5
                db.engine.max_overflow = 10
                db.engine.pool_timeout = 30
                db.engine.pool_recycle = 1800  # 30分钟
                logger.info("数据库连接池已配置")
            except Exception as e:
                logger.error(f"配置数据库连接池时出错: {str(e)}")
            
    except Exception as e:
        logger.error(f"工作进程初始化失败: {str(e)}")

@task_prerun.connect
def setup_task_context(task_id, task, *args, **kwargs):
    """
    任务执行前设置应用上下文
    """
    global flask_app
    
    if not flask_app:
        logger.error("任务执行前应用实例未初始化")
        try:
            from app import create_app
            flask_app = create_app()
            logger.info("已在任务执行前重新创建应用实例")
        except Exception as e:
            logger.error(f"在任务执行前重新创建应用实例失败: {str(e)}")
            return
    
    # 为任务创建应用上下文并存储在任务对象上
    try:
        logger.info(f"为任务 {task_id} 创建应用上下文")
        task._app_context = flask_app.app_context()
        task._app_context.push()
        
        # 确保数据库会话
        from app.extensions import db
        db.session.remove()
        
        logger.info(f"任务 {task_id} 的应用上下文已推送")
    except Exception as e:
        logger.error(f"设置任务 {task_id} 的应用上下文时出错: {str(e)}")

@task_postrun.connect
def cleanup_task_context(task_id, task, *args, **kwargs):
    """
    任务执行后清理应用上下文
    """
    try:
        if hasattr(task, '_app_context'):
            logger.info(f"清理任务 {task_id} 的应用上下文")
            
            # 清理数据库会话
            try:
                from app.extensions import db
                db.session.remove()
                logger.info(f"已清理任务 {task_id} 的数据库会话")
            except Exception as e:
                logger.error(f"清理任务 {task_id} 的数据库会话时出错: {str(e)}")
            
            # 弹出应用上下文
            task._app_context.pop()
            delattr(task, '_app_context')
            logger.info(f"已清理任务 {task_id} 的应用上下文")
    except Exception as e:
        logger.error(f"清理任务 {task_id} 的应用上下文时出错: {str(e)}")

@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """
    当Celery工作进程准备好接收任务时执行
    """
    logger.info(f"Celery工作进程准备就绪: {sender.hostname}")

@worker_process_shutdown.connect
def worker_shutdown(sender, **kwargs):
    """
    当Celery工作进程关闭时执行
    清理资源和连接
    """
    global flask_app
    
    logger.info(f"Celery工作进程关闭中: {sender.hostname if hasattr(sender, 'hostname') else 'unknown'}")
    
    # 清理数据库连接
    try:
        from app.extensions import db
        logger.info("正在关闭数据库连接池")
        db.session.remove()
        db.engine.dispose()
        logger.info("数据库连接池已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接池时出错: {str(e)}")
    
    # 重置全局应用实例
    flask_app = None
    
    logger.info("Celery工作进程已完全关闭")

# 如果在Flask上下文外运行，自动设置环境变量
if not os.environ.get('FLASK_APP'):
    os.environ['FLASK_APP'] = 'app'

# 仅在直接执行此文件时运行worker
if __name__ == '__main__':
    celery_app.start() 