#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务降级机制模块
提供服务降级和恢复功能
"""

import logging
import time
from typing import Dict, Any, Optional, Callable, List, Tuple
import threading
from functools import wraps

from app.core.services.service_state import state_manager, ServiceState

logger = logging.getLogger(__name__)

class FallbackManager:
    """
    服务降级管理器
    负责管理服务降级策略、降级处理和自动恢复
    """
    
    # 降级服务实例，格式: {服务名称: 降级服务实例}
    _fallback_services: Dict[str, Any] = {}
    
    # 恢复处理器，格式: {服务名称: (恢复函数, 恢复参数)}
    _recovery_handlers: Dict[str, Tuple[Callable, Dict[str, Any]]] = {}
    
    # 恢复线程
    _recovery_thread = None
    _should_stop = False
    
    # 锁，防止并发问题
    _lock = threading.Lock()
    
    @classmethod
    def register_fallback(cls, service_name: str, fallback_instance: Any) -> None:
        """
        注册服务的降级实现
        
        Args:
            service_name: 服务名称
            fallback_instance: 降级服务实例
        """
        with cls._lock:
            cls._fallback_services[service_name] = fallback_instance
            logger.info(f"已注册服务 '{service_name}' 的降级实现")
    
    @classmethod
    def register_recovery_handler(cls, service_name: str, handler: Callable, **kwargs) -> None:
        """
        注册服务的恢复处理器
        
        Args:
            service_name: 服务名称
            handler: 恢复函数
            **kwargs: 恢复函数的参数
        """
        with cls._lock:
            cls._recovery_handlers[service_name] = (handler, kwargs)
            logger.info(f"已注册服务 '{service_name}' 的恢复处理器")
    
    @classmethod
    def get_fallback(cls, service_name: str) -> Optional[Any]:
        """
        获取服务的降级实现
        
        Args:
            service_name: 服务名称
            
        Returns:
            Optional[Any]: 降级服务实例，如果不存在则返回None
        """
        return cls._fallback_services.get(service_name)
    
    @classmethod
    def degrade_service(cls, service_name: str, error: Optional[Exception] = None) -> bool:
        """
        将服务降级
        
        Args:
            service_name: 服务名称
            error: 导致降级的错误
            
        Returns:
            bool: 是否成功降级
        """
        with cls._lock:
            fallback = cls.get_fallback(service_name)
            if not fallback:
                logger.warning(f"服务 '{service_name}' 没有注册降级实现，无法降级")
                return False
                
            # 更新服务状态
            state_manager.update_service_state(service_name, ServiceState.DEGRADED, error)
            
            # 确保恢复线程正在运行
            cls._ensure_recovery_thread()
            
            logger.warning(f"服务 '{service_name}' 已降级运行")
            return True
    
    @classmethod
    def attempt_recovery(cls, service_name: str) -> bool:
        """
        尝试恢复服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            bool: 是否成功恢复
        """
        with cls._lock:
            if service_name not in cls._recovery_handlers:
                logger.warning(f"服务 '{service_name}' 没有注册恢复处理器，无法自动恢复")
                return False
            
            handler, kwargs = cls._recovery_handlers[service_name]
            try:
                # 更新状态为正在恢复
                logger.info(f"正在尝试恢复服务 '{service_name}'")
                
                # 调用恢复处理器
                result = handler(**kwargs)
                
                if result:
                    # 恢复成功，更新状态
                    state_manager.update_service_state(service_name, ServiceState.READY)
                    logger.info(f"服务 '{service_name}' 已成功恢复")
                    return True
                else:
                    logger.warning(f"服务 '{service_name}' 恢复失败")
                    return False
            except Exception as e:
                logger.error(f"恢复服务 '{service_name}' 时出错: {str(e)}")
                return False
    
    @classmethod
    def _ensure_recovery_thread(cls) -> None:
        """确保恢复线程正在运行"""
        if cls._recovery_thread is None or not cls._recovery_thread.is_alive():
            cls._should_stop = False
            cls._recovery_thread = threading.Thread(target=cls._recovery_worker, daemon=True)
            cls._recovery_thread.start()
    
    @classmethod
    def _recovery_worker(cls) -> None:
        """恢复线程工作函数"""
        logger.info("服务恢复线程已启动")
        
        while not cls._should_stop:
            with cls._lock:
                # 获取所有降级状态的服务
                degraded_services = []
                for service_name, info in state_manager.get_all_states().items():
                    if info.get('state') == ServiceState.DEGRADED.value:
                        degraded_services.append(service_name)
            
            # 尝试恢复每个降级服务
            for service_name in degraded_services:
                cls.attempt_recovery(service_name)
            
            # 等待一段时间再次尝试
            time.sleep(30)  # 每30秒尝试恢复一次
    
    @classmethod
    def stop(cls) -> None:
        """停止恢复线程"""
        cls._should_stop = True
        if cls._recovery_thread and cls._recovery_thread.is_alive():
            cls._recovery_thread.join(timeout=1.0)
            logger.info("服务恢复线程已停止")

# 全局降级管理器实例
fallback_manager = FallbackManager

# 装饰器，用于添加自动降级功能
def with_fallback(fallback_method: Optional[Callable] = None):
    """
    为方法添加自动降级功能的装饰器
    
    Args:
        fallback_method: 可选的降级方法，如果不提供则返回None
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"方法 {func.__name__} 执行失败，使用降级方法: {str(e)}")
                if fallback_method:
                    return fallback_method(*args, **kwargs)
                return None
        return wrapper
    return decorator 