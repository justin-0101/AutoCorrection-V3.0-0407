import logging
import threading
from typing import Any, Dict, Optional, Set
from enum import Enum
from app.core.services.service_priority import ServiceDefinition, ServicePriority
from app.core.services.service_lifecycle import lifecycle_manager, ServiceLifecycleEvent
from app.core.services.service_state import ServiceState, state_manager
from app.core.services.fallback_service import fallback_manager

logger = logging.getLogger('app.core.services')

class ServiceContainer:
    """服务容器，用于依赖注入和服务生命周期管理"""
    
    _instance = None
    _lock = threading.Lock()
    _services: Dict[str, Any] = {}
    _fallback_services: Dict[str, Any] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls) -> None:
        """初始化服务容器"""
        if cls._initialized:
            return
            
        with cls._lock:
            try:
                # 初始化核心服务
                from app.core.services.service_registry import ServiceRegistry
                ServiceRegistry.initialize_services()
                
                cls._initialized = True
                logger.info("服务容器初始化完成")
            except Exception as e:
                logger.error(f"服务容器初始化失败: {str(e)}")
                raise
    
    @classmethod
    def register(cls, service_name: str, service_instance: Any) -> Any:
        """
        注册服务到容器
        
        Args:
            service_name: 服务名称
            service_instance: 服务实例
            
        Returns:
            Any: 注册的服务实例
        """
        with cls._lock:
            # 更新服务状态为注册中
            state_manager.register_service(service_name)
            state_manager.update_service_state(service_name, ServiceState.REGISTERING)
            
            try:
                cls._services[service_name] = service_instance
                state_manager.update_service_state(service_name, ServiceState.READY)
                logger.info(f"服务已注册: {service_name}")
                return service_instance
            except Exception as e:
                state_manager.update_service_state(service_name, ServiceState.ERROR, error=e)
                logger.error(f"注册服务 '{service_name}' 失败: {str(e)}")
                raise
    
    @classmethod
    def get(cls, service_name: str) -> Optional[Any]:
        """
        获取服务实例
        
        Args:
            service_name: 服务名称
            
        Returns:
            Optional[Any]: 服务实例，如果不存在则返回None
        """
        if not cls._initialized:
            logger.warning("服务容器尚未初始化")
            return None
            
        service = cls._services.get(service_name)
        if not service:
            logger.warning(f"尝试获取未注册的服务 '{service_name}'")
            
            # 检查是否有降级实现
            fallback = fallback_manager.get_fallback(service_name)
            if fallback:
                logger.info(f"使用服务 '{service_name}' 的降级实现")
                return fallback
                
            return None
            
        # 验证服务状态
        state_info = state_manager.get_service_state(service_name)
        if not state_info or state_info.state != ServiceState.READY:
            logger.error(f"服务 '{service_name}' 未就绪")
            
            # 如果服务状态不是就绪状态，尝试使用降级实现
            if state_info and state_info.state == ServiceState.ERROR:
                fallback = fallback_manager.get_fallback(service_name)
                if fallback:
                    logger.info(f"服务 '{service_name}' 处于错误状态，使用降级实现")
                    fallback_manager.degrade_service(service_name, 
                                                   Exception(state_info.last_error))
                    return fallback
            
            return None
            
        # 检查依赖服务状态
        for dep in state_info.dependencies:
            if not cls.has(dep):
                logger.error(f"服务 '{service_name}' 的依赖 '{dep}' 未就绪")
                
                # 如果依赖不可用，尝试使用降级实现
                fallback = fallback_manager.get_fallback(service_name)
                if fallback:
                    logger.info(f"服务 '{service_name}' 的依赖不可用，使用降级实现")
                    fallback_manager.degrade_service(service_name, 
                                                   Exception(f"依赖 '{dep}' 不可用"))
                    return fallback
                
                return None
            
        return service
    
    @classmethod
    def has(cls, service_name: str) -> bool:
        """
        检查服务是否已注册
        
        Args:
            service_name: 服务名称
            
        Returns:
            bool: 服务是否已注册且就绪
        """
        if not cls._initialized:
            return False
            
        # 首先检查服务是否存在
        if service_name not in cls._services:
            return False
            
        # 然后检查服务状态
        state_info = state_manager.get_service_state(service_name)
        if not state_info or state_info.state != ServiceState.READY:
            return False
            
        # 最后检查依赖服务状态
        for dep in state_info.dependencies:
            if not cls.has(dep):
                return False
                
        return True
    
    @classmethod
    def register_fallback(cls, service_name: str, fallback_service: Any) -> None:
        """
        注册服务的降级实现
        
        Args:
            service_name: 服务名称
            fallback_service: 降级服务实例
        """
        fallback_manager.register_fallback(service_name, fallback_service)
    
    @classmethod
    def register_recovery_handler(cls, service_name: str, handler, **kwargs) -> None:
        """
        注册服务的恢复处理器
        
        Args:
            service_name: 服务名称
            handler: 恢复函数
            **kwargs: 恢复函数参数
        """
        fallback_manager.register_recovery_handler(service_name, handler, **kwargs)
    
    @classmethod
    def enable_mock_mode(cls) -> None:
        """启用模拟模式，用于测试环境"""
        from app.core.services.mock_services import get_mock_services
        mock_services = get_mock_services()
        for name, service in mock_services.items():
            cls.register_fallback(name, service)
        logger.info("已启用服务模拟模式")
    
    @classmethod
    def get_service_status(cls) -> Dict[str, Dict[str, Any]]:
        """获取所有服务的状态信息"""
        return state_manager.get_all_states()
    
    @classmethod
    def reset(cls) -> None:
        """重置服务容器（主要用于测试）"""
        with cls._lock:
            for service_name in cls._services:
                state_manager.update_service_state(service_name, ServiceState.STOPPING)
                
            cls._services.clear()
            cls._initialized = False
            
            for service_name in state_manager.get_all_states():
                state_manager.update_service_state(service_name, ServiceState.STOPPED)
                
            fallback_manager.stop()
            logger.info("服务容器已重置") 