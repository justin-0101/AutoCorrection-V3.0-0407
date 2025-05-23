#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery应用配置模块
为应用提供异步任务处理能力
"""

# 首先检查是否使用eventlet池，并应用猴子补丁
import os
import sys

# 强制应用eventlet猴子补丁，不再进行检查
try:
    print("正在应用eventlet猴子补丁...")
    import eventlet
    # 完全应用补丁，包括所有模块
    eventlet.monkey_patch(os=True, socket=True, time=True, thread=True, select=True)
    print("eventlet猴子补丁应用成功")
    # 标记已应用补丁
    eventlet.monkey_patched = True
except ImportError:
    print("警告: 未安装eventlet，请执行 pip install eventlet")
except Exception as e:
    print(f"应用eventlet猴子补丁失败: {str(e)}")

# 导入其他模块
import logging
from celery import Celery
# from celery.signals import worker_process_init, worker_ready, worker_process_shutdown # Temporarily remove signals
from app.config import Config

# 初始化日志
logger = logging.getLogger(__name__)
# flask_app = None # Temporarily remove global app

# def create_celery_app(): # Remove old function
#     ...

# ---- Flask-Celery 集成 ----
# 修改 Celery Task 基类以处理 Flask 上下文
# class FlaskTask(Celery.Task): # Temporarily remove FlaskTask definition
#     ...

# 使用新的 FlaskTask 创建 Celery 应用
celery_app = Celery(
    'app',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    # task_cls=FlaskTask # Still commented out
)

# 更新 Celery 配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    worker_pool='eventlet',  # 明确指定worker pool
    worker_concurrency=10,   # 并发数
)

# 导入信号处理器，确保它们被注册
# try: # Temporarily remove signal handler registration
#     from app.tasks.signal_handlers import register_signal_handlers
#     register_signal_handlers()
#     logging.getLogger(__name__).info("任务状态跟踪信号处理器已加载")
# except Exception as e:
#     logging.getLogger(__name__).warning(f"加载任务状态跟踪信号处理器失败: {str(e)}")

# 全局应用实例，确保在进程间共享 (FlaskTask 不再直接依赖它，但 init_worker_process 可能还用)
# flask_app = None # Already removed above

# @worker_process_init.connect # Temporarily remove worker_process_init
# def init_worker_process(*args, **kwargs):
#     ...

# @worker_ready.connect # Temporarily remove worker_ready
# def worker_ready_handler(*args, **kwargs):
#     ...

# @worker_process_shutdown.connect # Temporarily remove worker_process_shutdown
# def worker_shutdown_handler(*args, **kwargs):
#     ...

# 如果在Flask上下文外运行，自动设置环境变量
if not os.environ.get('FLASK_APP'):
    os.environ['FLASK_APP'] = 'app'

# 仅在直接执行此文件时运行worker
if __name__ == '__main__':
    celery_app.start()

# 连接到应用启动信号
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """设置定时任务"""
    # 导入任务调度器并设置任务
    from app.tasks.scheduler import setup_periodic_tasks as scheduler_setup
    scheduler_setup(sender, **kwargs) 