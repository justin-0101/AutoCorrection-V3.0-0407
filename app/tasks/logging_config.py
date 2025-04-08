#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务日志配置模块
配置Celery任务日志记录器和相关设置
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
import inspect

def setup_task_logging(task_name):
    """
    设置任务特定的日志记录器
    
    Args:
        task_name: 任务名称
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(f'app.tasks.{task_name}')
    logger.setLevel(logging.INFO)
    
    # 如果已经有处理器，则不重复添加
    if logger.handlers:
        return logger
    
    # 创建日志目录
    log_dir = os.environ.get('LOG_DIR', 'logs')
    task_log_dir = os.path.join(log_dir, 'tasks')
    if not os.path.exists(task_log_dir):
        os.makedirs(task_log_dir, exist_ok=True)
    
    # 创建文件处理器 - 任务特定的日志文件
    task_handler = RotatingFileHandler(
        os.path.join(task_log_dir, f'{task_name}.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    
    # 设置格式化器
    formatter = logging.Formatter(
        '[%(asctime)s] [%(process)d] [%(levelname)s] [%(name)s] %(message)s'
    )
    task_handler.setFormatter(formatter)
    
    # 添加到日志记录器
    logger.addHandler(task_handler)
    
    # 同时输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_task_logger(task_name=None):
    """
    获取任务特定的日志记录器
    
    Args:
        task_name: 任务名称或任务对象，如果未提供则自动检测调用者模块名称
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    if task_name is None:
        # 自动检测调用者模块名称
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
        if module:
            # 从模块路径中提取任务名称，例如 app.tasks.correction_tasks -> correction_tasks
            module_name = module.__name__
            if '.' in module_name:
                task_name = module_name.split('.')[-1]
            else:
                task_name = module_name
        else:
            # 如果无法检测，使用默认名称
            task_name = 'unknown_task'
    
    # 如果传入的是任务对象而不是字符串名称
    elif hasattr(task_name, 'name'):
        task_name = task_name.name
    
    # 提取任务名称的最后一部分，如 app.tasks.correction_tasks.process_essay_correction -> process_essay_correction
    elif isinstance(task_name, str) and '.' in task_name:
        task_name = task_name.split('.')[-1]
    
    return setup_task_logging(task_name)

def setup_celery_logging():
    """
    设置Celery日志记录
    
    Returns:
        logging.Logger: Celery根日志记录器
    """
    # 获取Celery日志记录器
    celery_logger = logging.getLogger('celery')
    celery_logger.setLevel(logging.INFO)
    
    # 如果已经有处理器，则不重复添加
    if celery_logger.handlers:
        return celery_logger
    
    # 创建日志目录
    log_dir = os.environ.get('LOG_DIR', 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 创建文件处理器
    handler = RotatingFileHandler(
        os.path.join(log_dir, 'celery.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    
    # 设置格式化器
    formatter = logging.Formatter(
        '[%(asctime)s] [%(process)d] [%(levelname)s] [%(name)s] %(message)s'
    )
    handler.setFormatter(formatter)
    
    # 添加到Celery日志记录器
    celery_logger.addHandler(handler)
    
    # 同时输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    celery_logger.addHandler(console_handler)
    
    return celery_logger

# 在导入时设置Celery日志
celery_logger = setup_celery_logging()
celery_logger.info("任务日志系统已初始化") 