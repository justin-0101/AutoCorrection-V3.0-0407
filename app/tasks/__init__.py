#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务模块初始化文件
配置Celery和任务
"""

# 1. 首先应用eventlet的猴子补丁
import os
import sys

# 检查是否使用eventlet池
if os.environ.get('CELERY_WORKER_POOL', '').lower() == 'eventlet' or '-P' in sys.argv and 'eventlet' in sys.argv:
    try:
        print("检测到使用eventlet池，应用eventlet猴子补丁...")
        import eventlet
        eventlet.monkey_patch()
        print("eventlet猴子补丁应用成功")
    except ImportError:
        print("警告: 使用eventlet池但未安装eventlet，请执行 pip install eventlet")
    except Exception as e:
        print(f"应用eventlet猴子补丁失败: {str(e)}")

# 2. 然后导入其他模块
import logging
from celery import Celery

# 初始化日志
logger = logging.getLogger(__name__)

# 创建Celery实例
celery = Celery('app')

# 使用配置模块配置Celery
celery.config_from_object('app.tasks.celery_config')

# 自动发现任务
celery.autodiscover_tasks(['app.tasks'])

# 导入任务模块
try:
    # 批改任务
    from app.tasks.correction_tasks import process_essay_correction
    # 用户任务 (如果存在)
    try:
        from app.tasks.user_tasks import process_user_tasks
    except ImportError:
        logger.debug("用户任务模块不存在或为空")
except Exception as e:
    logger.error(f"加载任务模块时出错: {str(e)}")

# 导出Celery实例
__all__ = ['celery'] 