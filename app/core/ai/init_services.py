#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务初始化模块
为Celery工作进程和Web应用提供服务初始化功能
"""

import logging
from app.core.services.container import container
from app.core.ai import AIClientFactory

logger = logging.getLogger(__name__)

def init_ai_services():
    """
    初始化AI相关服务
    确保AI客户端工厂被正确注册到服务容器
    
    Returns:
        bool: 初始化是否成功
    """
    try:
        # 检查是否已注册AI客户端工厂
        ai_factory = container.get("ai_client_factory")
        
        # 如果没有注册，则创建并注册
        if ai_factory is None:
            logger.info("AI客户端工厂未注册，正在创建并注册...")
            from app.core.ai import AIClientFactory, ai_client_factory
            # 使用已存在的全局实例而不是创建新实例
            container.register("ai_client_factory", ai_client_factory)
            logger.info("AI客户端工厂已成功注册")
        
        # 验证注册是否成功
        ai_factory = container.get("ai_client_factory")
        if ai_factory is None:
            raise RuntimeError("AI客户端工厂注册失败")
            
        return True
    except Exception as e:
        logger.error(f"初始化AI服务失败: {str(e)}")
        return False

def ensure_services():
    """
    确保所有必要的服务已初始化
    在Celery工作进程启动时调用
    
    Returns:
        bool: 所有服务初始化是否成功
    """
    success = True
    
    # 初始化AI服务
    if not init_ai_services():
        logger.error("AI服务初始化失败")
        success = False
    
    # 在这里添加其他服务的初始化
    
    return success 