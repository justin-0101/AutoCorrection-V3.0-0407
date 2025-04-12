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

# 导入信号处理器，确保它们被注册
try:
    from app.tasks.signal_handlers import register_signal_handlers
    register_signal_handlers()
    logging.getLogger(__name__).info("任务状态跟踪信号处理器已加载")
except Exception as e:
    logging.getLogger(__name__).warning(f"加载任务状态跟踪信号处理器失败: {str(e)}")

logger = logging.getLogger(__name__)

# 全局应用实例，确保在进程间共享
flask_app = None

@worker_process_init.connect
def init_worker_process(sender, **kwargs):
    """Celery工作进程初始化"""
    global flask_app
    
    try:
        # 创建Flask应用实例
        from app import create_app
        flask_app = create_app()
        
        if not flask_app:
            raise RuntimeError("无法创建Flask应用实例")
        
        logger.info("已成功创建Flask应用实例")
        
        # 初始化服务容器
        from app.core.services.container import container
        if not container._initialized:
            logger.info("初始化服务容器...")
            container.initialize()
        
        # 初始化依赖注入容器
        try:
            from app.core.services.service_registry_di import ServiceContainer
            ServiceContainer.init_worker()
            logger.info("依赖注入容器已初始化")
        except Exception as di_error:
            logger.warning(f"依赖注入容器初始化失败: {str(di_error)}")
        
        # 测试应用上下文
        with flask_app.app_context():
            # 测试数据库连接
            from app.extensions import db
            db.engine.dispose()  # 清理可能存在的连接
            db.session.remove()  # 清理会话
            
            # 配置数据库连接池
            db.engine.pool_size = 5
            db.engine.max_overflow = 10
            db.engine.pool_timeout = 30
            db.engine.pool_recycle = 1800  # 30分钟
            
            # 测试数据库连接
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            
            logger.info("数据库连接池配置和测试成功")
            
            # 初始化AI服务
            from app.core.ai.init_services import ensure_services
            if not ensure_services():
                raise RuntimeError("AI服务初始化失败")
            logger.info("AI服务初始化成功")
            
            logger.info("Flask应用和所有服务初始化成功")
            
    except Exception as e:
        logger.error(f"工作进程初始化失败: {str(e)}")
        # 强制退出工作进程
        os._exit(1)

@task_prerun.connect
def setup_task_context(task_id, task, *args, **kwargs):
    """任务执行前设置应用上下文"""
    global flask_app
    
    try:
        # 确保应用实例存在
        if not flask_app:
            from app import create_app
            flask_app = create_app()
            if not flask_app:
                raise RuntimeError("无法创建Flask应用实例")
        
        # 清理可能存在的旧上下文
        if hasattr(task, '_app_context'):
            try:
                task._app_context.pop()
            except Exception:
                pass
            delattr(task, '_app_context')
        
        # 创建新的上下文
        ctx = flask_app.app_context()
        ctx.push()
        task._app_context = ctx
        
        # 确保数据库会话干净
        from app.extensions import db
        db.session.remove()
        
        logger.info(f"任务 {task_id} 的应用上下文已设置")
        
    except Exception as e:
        logger.error(f"设置任务 {task_id} 的应用上下文时出错: {str(e)}")
        # 确保清理任何部分创建的上下文
        if hasattr(task, '_app_context'):
            try:
                task._app_context.pop()
            except Exception:
                pass
            delattr(task, '_app_context')
        raise  # 重新抛出异常，确保任务不会在无效上下文中执行

@task_postrun.connect
def cleanup_task_context(task_id, task, *args, **kwargs):
    """任务执行后清理应用上下文"""
    if not hasattr(task, '_app_context'):
        return
    
    try:
        # 清理数据库会话
        from app.extensions import db
        db.session.remove()
        
        # 弹出上下文
        task._app_context.pop()
        delattr(task, '_app_context')
        logger.info(f"任务 {task_id} 的应用上下文已清理")
        
    except Exception as e:
        logger.error(f"清理任务 {task_id} 的应用上下文时出错: {str(e)}")
        # 确保属性被删除
        if hasattr(task, '_app_context'):
            delattr(task, '_app_context')
        raise  # 重新抛出异常，以便Celery可以记录失败

@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """
    当Celery工作进程准备好接收任务时执行
    """
    logger.info(f"Celery工作进程准备就绪: {sender.hostname}")
    
    # 再次确保任务状态跟踪信号处理器已注册
    try:
        from app.tasks.signal_handlers import register_signal_handlers
        register_signal_handlers()
        logger.info("任务状态跟踪信号处理器已在worker启动时重新注册")
    except Exception as e:
        logger.warning(f"重新注册任务状态跟踪信号处理器失败: {str(e)}")

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