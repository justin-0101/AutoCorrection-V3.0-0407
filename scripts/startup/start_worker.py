#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
手动启动Celery Worker的辅助脚本
确保在启动Worker前正确初始化所有服务
"""

import os
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def setup_services():
    """初始化所有必要的服务"""
    logger.info("开始初始化应用服务...")
    
    try:
        # 创建Flask应用
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # 直接使用统一的服务初始化函数
            from app.core.services.__init__ import init_services
            init_services()
            
            logger.info("所有服务已成功初始化")
            return True
            
    except Exception as e:
        logger.error(f"初始化服务时出错: {str(e)}")
        logger.exception(e)
        return False

def start_worker():
    """启动Celery Worker"""
    if not setup_services():
        logger.error("由于服务初始化失败，未能启动Worker")
        return False
    
    logger.info("正在启动Celery Worker...")
    
    try:
        # 导入Celery应用实例
        from app.tasks.celery_app import celery_app
        
        # 加载所有任务
        from app.tasks import load_tasks
        if not load_tasks():
            logger.error("加载任务模块失败")
            return False
        
        # 启动Worker（通常这里只是准备工作，实际启动用命令行）
        logger.info("Celery Worker准备就绪，可以通过命令行启动:")
        logger.info("celery -A app.tasks.celery_app:celery_app worker --loglevel=info -Q default,correction,email")
        
        return True
    except Exception as e:
        logger.error(f"启动Worker时出错: {str(e)}")
        logger.exception(e)
        return False

if __name__ == "__main__":
    logger.info("==== 自动批改系统服务初始化 ====")
    if start_worker():
        logger.info("服务初始化成功，Worker准备就绪")
    else:
        logger.error("服务初始化失败") 