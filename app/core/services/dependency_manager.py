#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务依赖管理模块
提供服务依赖声明、依赖验证和依赖解析功能
"""

import logging
from typing import Dict, Set, List, Any, Optional, Callable, Tuple
import inspect
from functools import wraps
from app.core.services.service_state import state_manager, ServiceState

logger = logging.getLogger(__name__)

class DependencyManager:
    """服务依赖管理器"""
    
    # 记录所有已声明的依赖关系
    _dependencies: Dict[str, Set[str]] = {}
    
    # 记录服务初始化方法
    _initializers: Dict[str, Callable] = {}
    
    # 记录初始化顺序
    _initialization_order: List[str] = []
    
    @classmethod
    def declare_dependencies(cls, service_name: str, dependencies: List[str]) -> None:
        """
        声明服务依赖关系
        
        Args:
            service_name: 服务名称
            dependencies: 依赖服务名称列表
        """
        if service_name not in cls._dependencies:
            cls._dependencies[service_name] = set()
            
        # 添加新依赖
        for dep in dependencies:
            cls._dependencies[service_name].add(dep)
            
            # 更新状态管理器中的依赖关系
            state_info = state_manager.register_service(service_name)
            state_info.add_dependency(dep)
            
            # 更新被依赖服务的依赖者
            dep_state_info = state_manager.register_service(dep)
            dep_state_info.add_dependent(service_name)
            
        logger.info(f"已声明服务 '{service_name}' 的依赖: {', '.join(dependencies)}")
    
    @classmethod
    def register_initializer(cls, service_name: str, initializer: Callable) -> Callable:
        """
        注册服务初始化方法
        
        Args:
            service_name: 服务名称
            initializer: 初始化方法
            
        Returns:
            Callable: 原始初始化方法
        """
        cls._initializers[service_name] = initializer
        logger.info(f"已注册服务 '{service_name}' 的初始化方法")
        return initializer
    
    @classmethod
    def get_dependencies(cls, service_name: str) -> Set[str]:
        """获取服务的直接依赖"""
        return cls._dependencies.get(service_name, set())
    
    @classmethod
    def get_all_dependencies(cls, service_name: str) -> Set[str]:
        """
        获取服务的所有依赖（包括间接依赖）
        
        Args:
            service_name: 服务名称
            
        Returns:
            Set[str]: 所有依赖服务名称
        """
        result = set()
        visited = set()
        
        def collect_deps(svc_name):
            if svc_name in visited:
                return
                
            visited.add(svc_name)
            direct_deps = cls._dependencies.get(svc_name, set())
            result.update(direct_deps)
            
            for dep in direct_deps:
                collect_deps(dep)
                
        collect_deps(service_name)
        return result
    
    @classmethod
    def check_circular_dependencies(cls) -> Optional[List[str]]:
        """
        检查是否存在循环依赖
        
        Returns:
            Optional[List[str]]: 如果存在循环依赖，返回依赖路径；否则返回None
        """
        visited = set()
        path = []
        path_set = set()
        
        def dfs(service_name):
            if service_name in path_set:
                cycle_start = path.index(service_name)
                return path[cycle_start:] + [service_name]
                
            if service_name in visited:
                return None
                
            visited.add(service_name)
            path.append(service_name)
            path_set.add(service_name)
            
            for dep in cls._dependencies.get(service_name, set()):
                cycle = dfs(dep)
                if cycle:
                    return cycle
                    
            path.pop()
            path_set.remove(service_name)
            return None
            
        for service in cls._dependencies:
            cycle = dfs(service)
            if cycle:
                return cycle
                
        return None
    
    @classmethod
    def calculate_initialization_order(cls) -> List[str]:
        """
        计算服务初始化顺序
        
        Returns:
            List[str]: 服务初始化顺序
        """
        if cls._initialization_order:
            return cls._initialization_order
            
        # 检查循环依赖
        cycle = cls.check_circular_dependencies()
        if cycle:
            cycle_str = " -> ".join(cycle)
            logger.error(f"检测到循环依赖: {cycle_str}")
            raise ValueError(f"检测到循环依赖: {cycle_str}")
        
        # 拓扑排序
        result = []
        visited = set()
        temp_mark = set()
        
        def visit(service_name):
            if service_name in temp_mark:
                cycle_str = " -> ".join(temp_mark) + " -> " + service_name
                logger.error(f"检测到循环依赖: {cycle_str}")
                raise ValueError(f"检测到循环依赖: {cycle_str}")
                
            if service_name in visited:
                return
                
            if service_name in cls._dependencies:
                temp_mark.add(service_name)
                
                for dep in cls._dependencies[service_name]:
                    visit(dep)
                    
                temp_mark.remove(service_name)
                visited.add(service_name)
                result.append(service_name)
        
        # 确保所有服务都被访问
        all_services = set(cls._dependencies.keys())
        for dep_set in cls._dependencies.values():
            all_services.update(dep_set)
            
        for service in all_services:
            if service not in visited:
                visit(service)
                
        # 反转结果以获得正确的初始化顺序（从依赖最少的开始）
        cls._initialization_order = list(reversed(result))
        logger.info(f"计算的服务初始化顺序: {', '.join(cls._initialization_order)}")
        return cls._initialization_order
    
    @classmethod
    def initialize_services(cls, services_container) -> bool:
        """
        按顺序初始化所有服务
        
        Args:
            services_container: 服务容器对象
            
        Returns:
            bool: 是否成功初始化所有服务
        """
        try:
            # 计算初始化顺序
            init_order = cls.calculate_initialization_order()
            
            # 按顺序初始化
            for service_name in init_order:
                logger.info(f"初始化服务: {service_name}")
                state_manager.update_service_state(service_name, ServiceState.INITIALIZING)
                
                try:
                    # 如果服务已经在容器中
                    if services_container.has(service_name):
                        state_manager.update_service_state(service_name, ServiceState.READY)
                        continue
                        
                    # 如果有初始化方法
                    if service_name in cls._initializers:
                        initializer = cls._initializers[service_name]
                        service_instance = initializer()
                        if service_instance:
                            services_container.register(service_name, service_instance)
                        else:
                            logger.warning(f"服务 '{service_name}' 初始化方法返回None")
                            state_manager.update_service_state(service_name, ServiceState.ERROR)
                            return False
                    else:
                        logger.warning(f"服务 '{service_name}' 没有注册初始化方法")
                        state_manager.update_service_state(service_name, ServiceState.ERROR)
                
                except Exception as e:
                    logger.error(f"初始化服务 '{service_name}' 失败: {str(e)}")
                    state_manager.update_service_state(service_name, ServiceState.ERROR, error=e)
                    return False
            
            return True
        except Exception as e:
            logger.error(f"初始化服务失败: {str(e)}")
            return False

# 装饰器用于声明服务依赖
def requires(dependencies: List[str]):
    """
    声明服务依赖的装饰器
    
    Args:
        dependencies: 依赖服务名称列表
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        # 获取服务名称
        service_name = None
        if inspect.isclass(func):
            # 如果装饰的是类
            service_name = getattr(func, '__service_name__', func.__name__)
        elif inspect.isfunction(func):
            # 如果装饰的是函数
            service_name = func.__name__
            
        if not service_name:
            raise ValueError("无法确定服务名称，请使用@service_name装饰器先声明服务名称")
            
        # 声明依赖
        DependencyManager.declare_dependencies(service_name, dependencies)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 装饰器用于声明服务名称
def service_name(name: str):
    """
    声明服务名称的装饰器
    
    Args:
        name: 服务名称
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        func.__service_name__ = name
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 装饰器用于注册服务初始化方法
def initializer(service_name: str):
    """
    注册服务初始化方法的装饰器
    
    Args:
        service_name: 服务名称
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        DependencyManager.register_initializer(service_name, func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 全局依赖管理器实例
dependency_manager = DependencyManager 