#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务初始化模块
为Flask应用和Celery worker提供统一的服务初始化功能
"""

import logging
from app.core.services.container import container, ServiceScope
from app.core.ai import AIClientFactory
from app.core.redis_service import RedisService

logger = logging.getLogger(__name__)

def init_redis_service():
    """
    初始化Redis服务
    
    Returns:
        bool: 初始化是否成功
    """
    try:
        # 检查是否已注册Redis服务
        redis_service = container.get("redis_service")
        
        # 如果没有注册，则创建并注册
        if redis_service is None:
            logger.info("Redis服务未注册，正在创建并注册...")
            redis_service = RedisService()
            container.register("redis_service", redis_service, ServiceScope.SINGLETON)
            logger.info("Redis服务已成功注册")
        
        return True
    except Exception as e:
        logger.error(f"初始化Redis服务失败: {str(e)}")
        return False

def init_ai_services():
    """
    初始化AI相关服务
    
    Returns:
        bool: 初始化是否成功
    """
    try:
        # 检查是否已注册AI客户端工厂
        ai_factory = container.get("ai_client_factory")
        
        # 如果没有注册，则创建并注册
        if ai_factory is None:
            logger.info("AI客户端工厂未注册，正在创建并注册...")
            ai_factory = AIClientFactory()
            container.register("ai_client_factory", ai_factory, ServiceScope.SINGLETON)
            logger.info("AI客户端工厂已成功注册")
        
        return True
    except Exception as e:
        logger.error(f"初始化AI服务失败: {str(e)}")
        return False

def ensure_services():
    """
    确保所有必要的服务已初始化
    在Flask应用和Celery worker启动时调用
    
    Returns:
        bool: 所有服务初始化是否成功
    """
    success = True
    
    # 初始化Redis服务
    if not init_redis_service():
        logger.error("Redis服务初始化失败")
        success = False
    
    # 初始化AI服务
    if not init_ai_services():
        logger.error("AI服务初始化失败")
        success = False
    
    # 在这里添加其他服务的初始化
    
    return success 