#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务状态管理模块
提供服务生命周期状态跟踪和验证功能
"""

from enum import Enum
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ServiceState(Enum):
    """服务状态枚举"""
    UNREGISTERED = "unregistered"  # 未注册
    REGISTERING = "registering"    # 注册中
    INITIALIZING = "initializing"  # 初始化中
    READY = "ready"               # 就绪
    DEGRADED = "degraded"         # 降级
    ERROR = "error"               # 错误
    STOPPING = "stopping"         # 停止中
    STOPPED = "stopped"           # 已停止

class ServiceStateInfo:
    """服务状态信息"""
    def __init__(self, name: str):
        self.name = name
        self.state = ServiceState.UNREGISTERED
        self.last_state_change = datetime.utcnow()
        self.error_count = 0
        self.last_error = None
        self.metadata = {}
        self.dependencies = set()
        self.dependents = set()

    def update_state(self, new_state: ServiceState, error: Optional[Exception] = None) -> None:
        """
        更新服务状态
        
        Args:
            new_state: 新状态
            error: 可选的错误信息
        """
        old_state = self.state
        self.state = new_state
        self.last_state_change = datetime.utcnow()
        
        if error:
            self.error_count += 1
            self.last_error = str(error)
            
        logger.info(f"服务 '{self.name}' 状态从 {old_state.value} 变更为 {new_state.value}")
        
    def add_dependency(self, service_name: str) -> None:
        """添加依赖服务"""
        self.dependencies.add(service_name)
        
    def add_dependent(self, service_name: str) -> None:
        """添加依赖此服务的服务"""
        self.dependents.add(service_name)
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "state": self.state.value,
            "last_state_change": self.last_state_change.isoformat(),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "dependencies": list(self.dependencies),
            "dependents": list(self.dependents),
            "metadata": self.metadata
        }

class ServiceStateManager:
    """服务状态管理器"""
    
    def __init__(self):
        self._states: Dict[str, ServiceStateInfo] = {}
        
    def register_service(self, service_name: str) -> ServiceStateInfo:
        """
        注册服务并创建状态跟踪
        
        Args:
            service_name: 服务名称
            
        Returns:
            ServiceStateInfo: 服务状态信息对象
        """
        if service_name in self._states:
            logger.warning(f"服务 '{service_name}' 已注册")
            return self._states[service_name]
            
        state_info = ServiceStateInfo(service_name)
        self._states[service_name] = state_info
        logger.info(f"服务 '{service_name}' 已注册状态跟踪")
        return state_info
        
    def get_service_state(self, service_name: str) -> Optional[ServiceStateInfo]:
        """获取服务状态信息"""
        return self._states.get(service_name)
        
    def update_service_state(self, service_name: str, new_state: ServiceState, 
                           error: Optional[Exception] = None) -> None:
        """更新服务状态"""
        state_info = self._states.get(service_name)
        if state_info:
            state_info.update_state(new_state, error)
        else:
            logger.warning(f"尝试更新未注册服务 '{service_name}' 的状态")
            
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务的状态信息"""
        return {name: info.to_dict() for name, info in self._states.items()}
        
    def validate_service_ready(self, service_name: str) -> bool:
        """
        验证服务是否就绪
        
        Args:
            service_name: 服务名称
            
        Returns:
            bool: 服务是否就绪
        """
        state_info = self._states.get(service_name)
        if not state_info:
            logger.warning(f"尝试验证未注册服务 '{service_name}' 的状态")
            return False
            
        # 检查服务本身状态
        if state_info.state != ServiceState.READY:
            return False
            
        # 检查依赖服务状态
        for dep in state_info.dependencies:
            dep_state = self._states.get(dep)
            if not dep_state or dep_state.state != ServiceState.READY:
                return False
                
        return True

# 全局服务状态管理器实例
state_manager = ServiceStateManager() 