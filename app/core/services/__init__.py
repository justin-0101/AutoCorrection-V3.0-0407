"""
服务模块
提供服务容器和各种服务实例
"""
import logging
import os
from typing import Optional

from app.core.services.container import ServiceContainer, container, ServiceScope
from app.core.services.redis_service import RedisService

logger = logging.getLogger(__name__)

# 导出主要类和实例
__all__ = ['ServiceContainer', 'container', 'RedisService', 'init_services', 
           'get_redis_service', 'get_ai_client_factory', 'get_correction_service', 'get_ai_service']

def get_redis_service() -> Optional[RedisService]:
    """获取Redis服务实例"""
    try:
        redis_service = container.get("redis_service")
        if redis_service is None:
            logger.warning("Redis服务未找到，尝试动态初始化")
            from app.core.services.init_services import init_redis_service
            init_redis_service()
            redis_service = container.get("redis_service")
        return redis_service
    except Exception as e:
        logger.error(f"获取Redis服务失败: {str(e)}")
        return None

def get_ai_client_factory():
    """获取AI客户端工厂实例"""
    return container.get("ai_client_factory")

def get_correction_service():
    """获取批改服务实例"""
    return container.get("correction_service")

def get_ai_service():
    """
    获取AI服务实例
    如果服务未注册，则返回None
    """
    try:
        from app.core.ai import AIClientFactory, ai_client_factory
        return ai_client_factory.get_client()
    except Exception as e:
        logger.warning(f"获取AI服务失败: {str(e)}")
        return None

def init_services() -> None:
    """
    初始化所有核心服务
    按照依赖顺序注册到服务容器
    """
    logger.info("正在初始化核心服务...")
    
    # 1. 首先初始化Redis服务(基础设施服务)
    _init_redis_service()
    
    # 2. 初始化AI服务(依赖Redis服务)
    _init_ai_service()
    
    # 3. 初始化业务服务(依赖基础服务)
    _init_business_services()
    
    # 4. 初始化服务容器
    container.initialize()
    
    logger.info("核心服务初始化完成")

def _init_redis_service() -> None:
    """初始化Redis服务"""
    try:
        redis_service = RedisService()
        container.register("redis_service", redis_service, ServiceScope.SINGLETON)
        logger.info("Redis服务已注册到服务容器")
    except Exception as e:
        logger.error(f"Redis服务初始化失败: {str(e)}")
        raise RuntimeError("Redis服务是必需的基础服务") from e

def _init_ai_service() -> None:
    """初始化AI服务"""
    try:
        from app.core.ai import AIClientFactory
        ai_factory = AIClientFactory()
        container.register("ai_client_factory", ai_factory, ServiceScope.SINGLETON)
        logger.info("AI客户端工厂已注册到服务容器")
    except ImportError as e:
        logger.error(f"导入AI客户端工厂失败: {str(e)}")
        raise RuntimeError("AI服务是必需的") from e
    except Exception as e:
        logger.error(f"AI客户端工厂初始化失败: {str(e)}")
        raise RuntimeError("AI服务初始化失败") from e

def _init_business_services() -> None:
    """初始化业务服务"""
    try:
        from app.core.correction.correction_service import CorrectionService
        correction_service = CorrectionService()
        container.register("correction_service", correction_service, ServiceScope.SINGLETON)
        logger.info("批改服务已注册到服务容器")
    except ImportError as e:
        logger.error(f"导入批改服务失败: {str(e)}")
        raise RuntimeError("批改服务是必需的") from e
    except Exception as e:
        logger.error(f"批改服务初始化失败: {str(e)}")
        raise RuntimeError("批改服务初始化失败") from e 