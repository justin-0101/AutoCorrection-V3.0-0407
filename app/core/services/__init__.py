#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务模块
提供服务容器和各种服务实例
"""
import logging
import os
from typing import Optional
import traceback
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# 导出主要类和实例
__all__ = ['init_services', 'get_redis_service', 'get_ai_client_factory', 
           'get_correction_service', 'get_ai_service', 'get_file_service']

def _init_database() -> bool:
    """初始化并验证数据库连接"""
    try:
        from app.models.db import db
        with db.engine.connect() as conn:
            result = conn.execute(db.text("SELECT 1"))
            conn.commit()
        logger.info("数据库连接验证成功")
        return True
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return False

def get_redis_service():
    """获取Redis服务"""
    try:
        from app.core.services.service_registry_di import ServiceContainer
        di_container = ServiceContainer()
        # 尝试使用DI容器的resolve方法
        try:
            return di_container.resolve('redis_service')
        except (AttributeError, Exception):
            # 如果resolve方法不存在，尝试从静态容器获取
            from app.core.services.container import container
            return container.get('redis_service')
    except Exception as e:
        logger.warning(f"获取Redis服务失败: {str(e)}")
        return None

def get_ai_client_factory():
    """获取AI客户端工厂实例"""
    try:
        # 先尝试从DI容器获取
        from app.core.services.service_registry_di import ServiceContainer
        di_container = ServiceContainer()
        try:
            return di_container.resolve('ai_client_factory')
        except (AttributeError, Exception):
            # 如果失败，从静态容器获取
            from app.core.services.container import container
            return container.get('ai_client_factory')
    except Exception as e:
        logger.warning(f"获取AI客户端工厂失败: {str(e)}")
        return None

def get_correction_service():
    """获取批改服务实例"""
    try:
        # 先尝试从DI容器获取
        from app.core.services.service_registry_di import ServiceContainer
        di_container = ServiceContainer()
        try:
            return di_container.resolve('correction_service')
        except (AttributeError, Exception):
            # 如果失败，从静态容器获取
            from app.core.services.container import container
            return container.get('correction_service')
    except Exception as e:
        logger.warning(f"获取批改服务失败: {str(e)}")
        return None

def get_ai_service():
    """
    获取AI服务实例
    如果服务未注册，则返回None
    """
    try:
        ai_factory = get_ai_client_factory()
        if ai_factory:
            return ai_factory.get_client()
        return None
    except Exception as e:
        logger.warning(f"获取AI服务失败: {str(e)}")
        return None

def get_file_service():
    """获取文件服务实例"""
    try:
        # 先尝试从DI容器获取
        from app.core.services.service_registry_di import ServiceContainer
        di_container = ServiceContainer()
        try:
            return di_container.resolve('file_service')
        except (AttributeError, Exception):
            # 如果失败，从静态容器获取
            from app.core.services.container import container
            file_service = container.get('file_service')
            
            # 如果仍然失败，直接创建实例
            if file_service is None:
                from app.core.services.file_service import FileService
                file_service = FileService()
                # 尝试注册到容器
                try:
                    container.register('file_service', file_service, scope='singleton')
                except:
                    pass
                    
            return file_service
            
    except Exception as e:
        logger.warning(f"获取文件服务失败: {str(e)}")
        # 如果无法获取服务，尝试动态导入并创建
        try:
            from app.core.services.file_service import FileService
            return FileService()
        except ImportError:
            logger.error("无法导入文件服务")
            return None

def init_services() -> None:
    """
    初始化所有核心服务
    """
    logger.info("正在初始化核心服务...")
    
    try:
        # 从服务注册表初始化
        from app.core.services.service_registry_di import ServiceContainer
        
        # 创建容器实例
        container = ServiceContainer()
        logger.info("核心服务初始化完成")
        return container
    except Exception as e:
        logger.error(f"服务初始化失败: {str(e)}")
        raise RuntimeError("服务初始化失败") from e 