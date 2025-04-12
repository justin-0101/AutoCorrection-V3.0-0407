#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery 配置模块
用于配置 Celery 的日志和其他设置
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from celery.signals import after_setup_logger, after_setup_task_logger
from datetime import datetime

def setup_celery_logging(logger, **kwargs):
    """设置 Celery 日志配置"""
    # 创建日志目录
    log_dir = os.path.join('logs', 'celery')
    os.makedirs(log_dir, exist_ok=True)
    
    # 设置日志文件
    log_file = os.path.join(log_dir, f'celery_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
    
    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # 设置日志级别
    logger.setLevel(logging.INFO)
    
    # 移除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 添加新的处理器
    logger.addHandler(file_handler)
    
    # 确保日志立即写入文件
    file_handler.flush()

@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """设置 Celery 主日志记录器"""
    setup_celery_logging(logger, **kwargs)

@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    """设置 Celery 任务日志记录器"""
    setup_celery_logging(logger, **kwargs) 