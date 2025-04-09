#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务注册表模块
提供服务的自动发现、注册和初始化功能
"""

import logging
import importlib
import pkgutil
import inspect
from typing import Dict, Any, Callable, List, Optional

from app.core.services.service_container import ServiceContainer
from app.core.services.service_state import ServiceState, state_manager
from app.core.services.dependency_manager import dependency_manager
from app.core.db import get_session

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """服务注册表，管理服务的注册和初始化"""
    
    # 核心服务定义，格式: {服务名称: (模块路径, 类名)}
    CORE_SERVICES = {
        'redis_service': ('app.core.services.redis_service', 'RedisService'),
        'ai_client_factory': ('app.core.ai', 'AIClientFactory'),
        'correction_service': ('app.core.correction.correction_service', 'CorrectionService'),
        'source_type_manager': ('app.core.source_type_manager', 'SourceTypeManager'),
        'notification_service': ('app.core.notification.notification_service', 'NotificationService'),
    }
    
    # 服务实例缓存
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def initialize_services(cls) -> bool:
        """
        初始化所有服务
        
        Returns:
            bool: 是否成功初始化所有服务
        """
        try:
            logger.info("开始初始化服务...")
            
            # 声明核心服务依赖关系
            cls._declare_core_dependencies()
            
            # 获取初始化顺序并初始化服务
            return dependency_manager.initialize_services(ServiceContainer)
            
        except Exception as e:
            logger.error(f"初始化服务失败: {str(e)}")
            
            # 尝试初始化关键服务，即使其他服务失败
            try:
                logger.info("尝试单独初始化关键服务...")
                # 初始化Redis服务 - 这是最基础的服务
                cls._initialize_service('redis_service')
                # 初始化AI客户端工厂 - 核心功能依赖此服务
                cls._initialize_service('ai_client_factory')
                return True
            except Exception as recovery_error:
                logger.error(f"恢复初始化失败: {str(recovery_error)}")
                return False
            
    @classmethod
    def _initialize_service(cls, service_name: str) -> Any:
        """
        单独初始化特定服务
        
        Args:
            service_name: 要初始化的服务名称
            
        Returns:
            Any: 初始化的服务实例
        """
        if service_name not in cls.CORE_SERVICES:
            logger.error(f"未知的服务: {service_name}")
            return None
            
        module_path, class_name = cls.CORE_SERVICES[service_name]
        
        try:
            # 导入模块
            module = importlib.import_module(module_path)
            # 获取类
            service_class = getattr(module, class_name)
            # 创建实例
            service_instance = service_class()
            
            # 注册到服务容器
            from app.core.services.container import container, ServiceScope
            container.register(service_name, service_instance, ServiceScope.SINGLETON)
            
            logger.info(f"成功初始化服务: {service_name}")
            return service_instance
        except Exception as e:
            logger.error(f"初始化服务 {service_name} 失败: {str(e)}")
            return None
    
    @classmethod
    def _declare_core_dependencies(cls) -> None:
        """声明核心服务的依赖关系"""
        # AI客户端工厂不依赖其他服务
        dependency_manager.declare_dependencies('ai_client_factory', [])
        
        # Redis服务不依赖其他服务
        dependency_manager.declare_dependencies('redis_service', [])
        
        # 批改服务依赖AI客户端工厂
        dependency_manager.declare_dependencies('correction_service', ['ai_client_factory'])
        
        # 通知服务依赖Redis服务
        dependency_manager.declare_dependencies('notification_service', ['redis_service'])
        
        # 来源类型管理器不依赖其他服务
        dependency_manager.declare_dependencies('source_type_manager', [])
    
    @classmethod
    def initialize_service(cls, service_name: str) -> Any:
        """
        初始化单个服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            Any: 服务实例，如果初始化失败则返回None
        """
        # 如果服务已经初始化
        if service_name in cls._instances:
            return cls._instances[service_name]
            
        # 更新状态为初始化中
        state_manager.update_service_state(service_name, ServiceState.INITIALIZING)
        
        try:
            # 如果是核心服务
            if service_name in cls.CORE_SERVICES:
                module_path, class_name = cls.CORE_SERVICES[service_name]
                
                # 导入模块
                module = importlib.import_module(module_path)
                service_class = getattr(module, class_name)
                
                # 创建实例
                service_instance = service_class()
                
                # 注册服务
                try:
                    from app.core.db.transaction import atomic_operation
                    
                    with atomic_operation(f"注册服务 {service_name}"):
                        ServiceContainer.register(service_name, service_instance)
                except ImportError:
                    # 如果事务模块尚未初始化，则直接注册
                    ServiceContainer.register(service_name, service_instance)
                
                # 缓存实例
                cls._instances[service_name] = service_instance
                
                logger.info(f"服务 '{service_name}' 已初始化")
                return service_instance
            else:
                # 尝试查找已注册的初始化器
                initializer = dependency_manager._initializers.get(service_name)
                if initializer:
                    service_instance = initializer()
                    if service_instance:
                        # 注册服务
                        try:
                            from app.core.db.transaction import atomic_operation
                            
                            with atomic_operation(f"注册服务 {service_name}"):
                                ServiceContainer.register(service_name, service_instance)
                        except ImportError:
                            # 如果事务模块尚未初始化，则直接注册
                            ServiceContainer.register(service_name, service_instance)
                            
                        cls._instances[service_name] = service_instance
                        return service_instance
                
                logger.warning(f"未找到服务 '{service_name}' 的定义")
                return None
                
        except Exception as e:
            logger.error(f"初始化服务 '{service_name}' 失败: {str(e)}")
            state_manager.update_service_state(service_name, ServiceState.ERROR, error=e)
            return None
    
    @classmethod
    def reset(cls) -> None:
        """重置服务注册表（主要用于测试）"""
        cls._instances.clear()
        logger.info("服务注册表已重置")
    
    @classmethod
    def discover_services(cls) -> List[str]:
        """
        自动发现可用服务
        
        Returns:
            List[str]: 发现的服务名称列表
        """
        services = []
        
        def scan_package(package_name):
            try:
                package = importlib.import_module(package_name)
                for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                    if is_pkg:
                        scan_package(name)
                    else:
                        try:
                            module = importlib.import_module(name)
                            for obj_name in dir(module):
                                obj = getattr(module, obj_name)
                                if inspect.isclass(obj) and hasattr(obj, '__service_name__'):
                                    services.append(getattr(obj, '__service_name__'))
                        except ImportError:
                            continue
            except (ImportError, AttributeError):
                pass
        
        # 扫描核心包
        scan_package('app.core')
        
        return services

# 全局服务注册表实例
service_registry = ServiceRegistry 