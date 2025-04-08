from functools import wraps
import logging
from app.core.services.service_container import ServiceContainer

logger = logging.getLogger('app.core.services')

def auto_register(service_name):
    """
    服务自动注册装饰器
    
    Args:
        service_name: 服务名称
        
    Returns:
        装饰器函数
    """
    def decorator(cls):
        # 保存原始的__init__方法
        original_init = cls.__init__
        
        @wraps(original_init)
        def __init__wrapper(self, *args, **kwargs):
            # 调用原始的__init__
            original_init(self, *args, **kwargs)
            
            # 注册到服务容器
            ServiceContainer.register(service_name, self)
            logger.info(f"服务 '{service_name}' 已自动注册")
            
        # 替换__init__方法
        cls.__init__ = __init__wrapper
        
        # 添加类属性，标记为自动注册服务
        cls.__service_name__ = service_name
        
        return cls
    
    return decorator 