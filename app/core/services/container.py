#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务容器模块
提供依赖注入和服务管理功能
"""
from enum import Enum
import logging
from typing import Any, Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)

class ServiceScope(Enum):
    """服务生命周期范围"""
    SINGLETON = "singleton"  # 全局单例
    REQUEST = "request"    # 请求级别
    TRANSIENT = "transient"  # 临时实例

class ServiceDefinition:
    """服务定义"""
    def __init__(self, instance: Any = None, scope: ServiceScope = ServiceScope.SINGLETON):
        self.instance = instance
        self.scope = scope

class ServiceContainer:
    """服务容器,提供依赖注入和服务管理"""
    
    def __init__(self):
        self._services: Dict[str, ServiceDefinition] = {}
        self._lock = Lock()
        self._initialized = False
    
    def register(self, name: str, instance: Any, scope: ServiceScope = ServiceScope.SINGLETON) -> None:
        """
        注册服务
        
        Args:
            name: 服务名称
            instance: 服务实例
            scope: 服务生命周期范围
        """
        with self._lock:
            if name in self._services:
                logger.warning(f"服务 '{name}' 已存在,将被覆盖")
            
            self._services[name] = ServiceDefinition(instance, scope)
            logger.info(f"服务 '{name}' 已注册 (scope: {scope.value})")
    
    def get(self, name: str) -> Optional[Any]:
        """
        获取服务实例
        
        Args:
            name: 服务名称
            
        Returns:
            服务实例,如果不存在则返回None
        """
        # 移除初始化检查，确保即使容器未初始化也能获取已注册的服务
        # if not self._initialized:
        #     logger.warning("服务容器尚未初始化")
        #     return None
            
        service_def = self._services.get(name)
        if not service_def:
            logger.warning(f"尝试获取未注册的服务 '{name}'")
            return None
            
        if service_def.scope == ServiceScope.TRANSIENT:
            # 临时实例每次都创建新的
            return service_def.instance.__class__()
            
        return service_def.instance
    
    def has(self, name: str) -> bool:
        """
        检查服务是否已注册
        
        Args:
            name: 服务名称
            
        Returns:
            bool: 是否已注册
        """
        return name in self._services
    
    def initialize(self) -> None:
        """初始化服务容器"""
        if self._initialized:
            return
            
        with self._lock:
            if self._initialized:  # 双重检查锁定
                return
                
            # 验证所有必需的服务
            self._validate_required_services()
            
            self._initialized = True
            logger.info("服务容器初始化完成")
    
    def _validate_required_services(self) -> None:
        """验证所有必需的服务是否已注册"""
        required_services = [
            'redis_service',
            'ai_client_factory',
            'correction_service'
        ]
        
        missing_services = []
        for service_name in required_services:
            if not self.has(service_name):
                missing_services.append(service_name)
        
        if missing_services:
            logger.warning(f"以下必需服务未注册: {', '.join(missing_services)}")
    
    def reset(self) -> None:
        """重置服务容器(主要用于测试)"""
        with self._lock:
            self._services.clear()
            self._initialized = False

# 全局服务容器实例
container = ServiceContainer() 