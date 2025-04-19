#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务容器模块，用于管理应用中的服务实例
"""

import logging
from typing import Dict, Any, Optional, Type
from enum import Enum, auto

logger = logging.getLogger(__name__)

class ServiceScope(Enum):
    """服务作用域"""
    SINGLETON = auto()    # 单例服务，整个应用生命周期只有一个实例
    SCOPED = auto()       # 作用域服务，每个请求一个实例
    TRANSIENT = auto()    # 瞬态服务，每次获取都创建新实例

class ServiceContainer:
    """
    服务容器，用于注册、获取和管理应用中的服务实例
    使用单例模式确保容器在应用中是唯一的
    """
    _instance = None
    _services: Dict[str, Any] = {}
    _scopes: Dict[str, ServiceScope] = {}
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceContainer, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, name: str, service: Any, scope: ServiceScope = ServiceScope.SINGLETON) -> None:
        """
        注册服务到容器
        
        Args:
            name: 服务名称
            service: 服务实例或类型
            scope: 服务作用域
        """
        if name in cls._services:
            logger.warning(f"服务 '{name}' 已存在，将被覆盖")
        cls._services[name] = service
        cls._scopes[name] = scope
        logger.info(f"服务 '{name}' 已注册 (scope: {scope.name.lower()})")
    
    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        """
        从容器获取服务
        
        Args:
            name: 服务名称
            
        Returns:
            服务实例，如果不存在则返回None
        """
        if not cls.has(name):
            logger.warning(f"尝试获取未注册的服务 '{name}' ")
            return None
        
        return cls._services.get(name)
    
    @classmethod
    def has(cls, name: str) -> bool:
        """
        检查服务是否存在
        
        Args:
            name: 服务名称
            
        Returns:
            如果服务存在则返回True，否则返回False
        """
        return name in cls._services
    
    @classmethod
    def remove(cls, name: str) -> None:
        """
        从容器中移除服务
        
        Args:
            name: 服务名称
        """
        if name in cls._services:
            del cls._services[name]
            if name in cls._scopes:
                del cls._scopes[name]
            logger.debug(f"服务 '{name}' 已移除")
        else:
            logger.warning(f"尝试移除不存在的服务 '{name}'")
    
    @classmethod
    def clear(cls) -> None:
        """
        清空容器中的所有服务
        """
        cls._services.clear()
        cls._scopes.clear()
        logger.debug("所有服务已清空")
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """
        获取所有注册的服务
        
        Returns:
            包含所有服务的字典
        """
        return cls._services.copy()
    
    @classmethod
    def initialize(cls) -> None:
        """
        初始化容器
        在所有服务注册完成后调用
        """
        cls._initialized = True
        logger.info("服务容器初始化完成")
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查容器是否已初始化
        
        Returns:
            如果容器已初始化则返回True，否则返回False
        """
        return cls._initialized

# 创建全局容器实例
container = ServiceContainer() 