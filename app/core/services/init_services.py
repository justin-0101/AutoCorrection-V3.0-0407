#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务初始化模块
为Flask应用和Celery worker提供统一的服务初始化功能
"""

import logging
import os
from app.core.services.container import container, ServiceScope
from app.core.ai import AIClientFactory
from app.core.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class MockRedis:
    """Redis的模拟实现，用于Redis服务器不可用时"""
    def __init__(self):
        self.data = {}
        self.hash_data = {}
        logger.info("使用Redis模拟实现")
    
    def ping(self):
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, ex=None):
        self.data[key] = value
        return True
    
    def setex(self, key, time, value):
        """设置键值对并指定过期时间"""
        self.data[key] = value
        return True
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
        return True
    
    def exists(self, key):
        return key in self.data
        
    def hset(self, name, key, value):
        if name not in self.hash_data:
            self.hash_data[name] = {}
        self.hash_data[name][key] = value
        return True
    
    def hget(self, name, key):
        if name in self.hash_data and key in self.hash_data[name]:
            return self.hash_data[name][key]
        return None
    
    def hgetall(self, name):
        return self.hash_data.get(name, {})

def init_redis_service():
    """
    初始化Redis服务
    如果Redis不可用，使用内存模拟实现
    
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
            from app.core.ai import AIClientFactory
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