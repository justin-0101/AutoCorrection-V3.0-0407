#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务初始化注册表模块
负责在应用启动时注册和初始化所有必要的服务
"""

import logging
from flask import Flask
from typing import List, Dict, Any, Optional

from app.core.services.container import ServiceContainer
from app.core.file.file_service import FileService
from app.core.correction.ai_corrector import AICorrectionService
from app.core.ai.deepseek_client import DeepseekClient

logger = logging.getLogger(__name__)

# 需要注册的服务列表
REQUIRED_SERVICES = [
    'file_service',
    'correction_service',
    'ai_client'
]

def register_all_services() -> bool:
    """
    注册所有服务
    
    Returns:
        bool: 所有服务是否注册成功
    """
    logger.info("开始注册所有服务...")
    container = ServiceContainer()
    
    # 注册文件服务
    try:
        file_service = FileService()
        container.register('file_service', file_service)
        logger.info("文件服务注册成功")
    except Exception as e:
        logger.error(f"文件服务注册失败: {str(e)}")
        return False
    
    # 注册AI客户端
    try:
        ai_client = DeepseekClient()
        container.register('ai_client', ai_client)
        logger.info("AI客户端注册成功")
    except Exception as e:
        logger.error(f"AI客户端注册失败: {str(e)}")
        return False
    
    # 注册修正服务
    try:
        correction_service = AICorrectionService(ai_client)
        container.register('correction_service', correction_service)
        logger.info("修正服务注册成功")
    except Exception as e:
        logger.error(f"修正服务注册失败: {str(e)}")
        return False
    
    # 验证所有必需服务是否已注册
    missing_services = []
    for service_name in REQUIRED_SERVICES:
        if not container.has(service_name):
            missing_services.append(service_name)
    
    if missing_services:
        logger.warning(f"以下必需服务未注册: {', '.join(missing_services)}")
        return False
    
    logger.info("所有服务注册完成")
    return True

def init_services_with_app(app: Flask) -> bool:
    """
    使用Flask应用上下文初始化服务
    
    Args:
        app: Flask应用实例
        
    Returns:
        bool: 服务初始化是否成功
    """
    with app.app_context():
        success = register_all_services()
        
        if success:
            logger.info("服务初始化成功")
            
            # 验证文件服务是否可用
            container = ServiceContainer()
            file_service = container.get('file_service')
            if file_service:
                logger.info("文件服务可用")
            else:
                logger.error("文件服务不可用")
                return False
            
            return True
        else:
            logger.error("服务初始化失败")
            return False 