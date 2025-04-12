#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务注册表模块 - 依赖注入版本
为应用提供依赖注入方式的服务注册和管理
"""

import logging
import importlib
from typing import Dict, Any, List, Optional, Type
import yaml
import os

from dependency_injector import containers, providers
from app.core.ai import AIClientFactory
from app.core.correction.correction_service import CorrectionService

logger = logging.getLogger(__name__)

class ServiceContainer(containers.DeclarativeContainer):
    """应用服务容器"""
    
    # 配置
    config = providers.Configuration()
    config.from_yaml('config/services.yaml')
    
    # 加载环境变量
    config.ai.api_key.from_env('AI_API_KEY')
    config.ai.endpoint.from_env('AI_API_ENDPOINT')
    config.redis.host.from_env('REDIS_HOST', 'localhost')
    config.redis.port.from_env('REDIS_PORT', '6379')
    config.redis.password.from_env('REDIS_PASSWORD', '')
    
    # 核心服务
    ai_client_factory = providers.Singleton(
        AIClientFactory,
        api_key=config.ai.api_key,
        endpoint=config.ai.endpoint,
        model=config.ai.model,
        timeout=config.ai.timeout
    )
    
    # Redis服务
    redis_service = providers.Singleton(
        'app.core.services.redis_service.RedisService',
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        password=config.redis.password
    )
    
    # 批改服务
    correction_service = providers.Singleton(
        CorrectionService
    )
    
    # 健康检查服务
    health_checker = providers.Singleton(
        'app.core.services.health_checker.HealthChecker'
    )
    
    # 依赖关系可视化
    @classmethod
    def visualize_dependencies(cls) -> Optional[str]:
        """
        生成服务依赖关系图
        
        Returns:
            str: 生成的图形代码（如果graphviz可用）
        """
        try:
            import graphviz
            dot = graphviz.Digraph(comment='Service Dependencies')
            
            # 添加节点
            services = cls.get_services()
            for service_name in services:
                dot.node(service_name, service_name)
            
            # 添加边
            dependencies = cls.get_dependencies()
            for service, deps in dependencies.items():
                for dep in deps:
                    dot.edge(service, dep)
            
            # 尝试保存和返回
            dot_code = dot.source
            try:
                dot.render('docs/service_dependencies', format='png', cleanup=True)
                logger.info(f"依赖图已保存到 docs/service_dependencies.png")
            except Exception as e:
                logger.warning(f"无法保存依赖图: {str(e)}")
                
            return dot_code
            
        except ImportError:
            logger.warning("无法生成依赖图，graphviz包未安装")
            return None
    
    @classmethod
    def get_services(cls) -> List[str]:
        """获取所有注册的服务名称"""
        result = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, providers.Provider) and not attr_name.startswith('_'):
                result.append(attr_name)
        return result
    
    @classmethod
    def get_dependencies(cls) -> Dict[str, List[str]]:
        """获取服务依赖关系"""
        result = {}
        # 硬编码依赖关系（理想情况下应自动检测）
        result['correction_service'] = ['ai_client_factory']
        result['health_checker'] = ['redis_service', 'correction_service']
        return result
    
    @classmethod
    def init_app(cls, app):
        """初始化Flask应用"""
        if app:
            # 从Flask配置更新
            if 'SERVICES_CONFIG' in app.config:
                cls.config.from_dict(app.config['SERVICES_CONFIG'])
                
            # 注入依赖
            cls.wire(modules=[
                "app.tasks.correction_tasks",
                "app.core.correction.correction_service",
                "app.api.v1.essays.routes",
                "app.routes.main_routes"
            ])
            
            # 记录初始化信息
            logger.info("服务容器已连接到应用")
        else:
            logger.warning("无法初始化应用，未提供有效的Flask应用实例")
            
    @classmethod
    def init_worker(cls):
        """初始化Celery工作进程"""
        # 更新配置
        try:
            env_file = os.environ.get('ENV_FILE', '.env')
            if os.path.exists(env_file):
                import dotenv
                dotenv.load_dotenv(env_file)
                logger.info(f"已从 {env_file} 加载环境变量")
        except ImportError:
            logger.warning("无法加载dotenv，环境变量可能未正确设置")
            
        # 注入依赖
        cls.wire(modules=[
            "app.tasks.correction_tasks",
            "app.core.correction.correction_service"
        ])
        
        logger.info("服务容器已连接到Celery工作进程") 