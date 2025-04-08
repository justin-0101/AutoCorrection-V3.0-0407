from enum import IntEnum
from typing import Dict, List, Set

class ServicePriority(IntEnum):
    """服务初始化优先级定义"""
    DATABASE = 0
    REDIS = 1
    AI_CLIENT = 2
    CORRECTION = 3
    SOURCE_TYPE = 4
    MONITORING = 5

class ServiceDefinition:
    """服务定义，包含依赖关系"""
    SERVICES: Dict[str, 'ServiceDefinition'] = {}
    
    def __init__(self, name: str, priority: ServicePriority, dependencies: List[str] = None):
        self.name = name
        self.priority = priority
        self.dependencies = set(dependencies or [])
        self._initialized = False
        ServiceDefinition.SERVICES[name] = self
    
    @property
    def initialized(self) -> bool:
        return self._initialized
    
    @initialized.setter
    def initialized(self, value: bool):
        self._initialized = value
    
    @classmethod
    def get_initialization_order(cls) -> List[str]:
        """获取考虑依赖关系的初始化顺序"""
        result = []
        visited = set()
        
        def visit(service_name: str, path: Set[str]):
            if service_name in path:
                raise ValueError(f"检测到循环依赖: {' -> '.join(path)} -> {service_name}")
            if service_name in visited:
                return
            
            service = cls.SERVICES[service_name]
            path.add(service_name)
            
            for dep in service.dependencies:
                if dep not in cls.SERVICES:
                    raise ValueError(f"服务 {service_name} 依赖未定义的服务: {dep}")
                visit(dep, path.copy())
            
            visited.add(service_name)
            result.append(service_name)
        
        # 按优先级排序服务
        services = sorted(cls.SERVICES.keys(), 
                        key=lambda x: cls.SERVICES[x].priority)
        
        # 处理每个服务的依赖
        for service_name in services:
            if service_name not in visited:
                visit(service_name, set())
        
        return result

# 定义核心服务
ServiceDefinition('database', ServicePriority.DATABASE)
ServiceDefinition('redis_service', ServicePriority.REDIS, ['database'])
ServiceDefinition('ai_client_factory', ServicePriority.AI_CLIENT, ['redis_service'])
ServiceDefinition('correction_service', ServicePriority.CORRECTION, ['ai_client_factory'])
ServiceDefinition('source_type_manager', ServicePriority.SOURCE_TYPE, ['database'])
ServiceDefinition('monitoring', ServicePriority.MONITORING) 