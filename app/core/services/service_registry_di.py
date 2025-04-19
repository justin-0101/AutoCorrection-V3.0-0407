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
import sys

from dependency_injector import containers, providers
from app.core.ai import AIClientFactory
from app.core.correction.correction_service import CorrectionService
from app.core.correction.ai_corrector import AICorrectionService

logger = logging.getLogger(__name__)

class ServiceContainer(containers.DeclarativeContainer):
    """应用服务容器"""
    
    # 配置
    config = providers.Configuration()
    
    # 手动读取YAML配置文件，指定UTF-8编码
    try:
        # 获取当前工作目录并构建绝对路径
        current_dir = os.getcwd()
        config_path = os.path.join(current_dir, 'config', 'services.yaml')
        logger.info(f"尝试从路径加载配置: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as yaml_file:
            yaml_config = yaml.safe_load(yaml_file)
            config.from_dict(yaml_config)
            logger.info("成功以UTF-8编码加载YAML配置文件")
    except Exception as e:
        logger.error(f"加载YAML配置文件失败: {str(e)}")
        # 使用空字典作为默认配置
        config.from_dict({})
        # 创建基本配置以确保系统可以启动
        config.ai.api_key.with_default('default_key')
        config.ai.endpoint.with_default('https://api.default.com')
        config.ai.model.with_default('dash-pro')
        config.ai.timeout.with_default(60)
        config.redis.host.with_default('localhost')
        config.redis.port.with_default(6379)
        config.redis.db.with_default(0)
        config.redis.password.with_default('')
    
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
    
    # 文件服务
    file_service = providers.Singleton(
        'app.core.services.file_service.FileService'
    )
    
    # AI批改服务
    ai_correction_service = providers.Singleton(
        AICorrectionService,
        ai_service="deepseek",  # 直接使用字符串默认值
        debug_mode=True  # 直接启用调试模式
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
        result['ai_correction_service'] = ['ai_client_factory']
        result['correction_service'] = ['ai_correction_service']
        result['health_checker'] = ['redis_service', 'correction_service']
        return result
    
    @classmethod
    def init_app(cls, app):
        """初始化Flask应用"""
        if app:
            # 从Flask配置更新
            if 'SERVICES_CONFIG' in app.config:
                cls.config.from_dict(app.config['SERVICES_CONFIG'])
                
            # 创建容器实例
            container = cls()
            
            # 手动导入并注入依赖
            modules_to_inject = [
                "app.tasks.correction_tasks",
                "app.core.correction.correction_service",
                "app.api.v1.essays.routes",
                "app.routes.main_routes"
            ]
            
            for module_name in modules_to_inject:
                try:
                    # 尝试导入模块
                    if module_name in sys.modules:
                        module = sys.modules[module_name]
                    else:
                        module = importlib.import_module(module_name)
                    
                    # 为模块设置容器属性
                    module.container = container
                    logger.info(f"为模块 {module_name} 注入了依赖")
                except (ImportError, AttributeError) as e:
                    logger.warning(f"无法为模块 {module_name} 注入依赖: {str(e)}")
            
            # 记录初始化信息
            logger.info("服务容器已连接到应用")
            
            # 将容器设置为全局可访问
            app.container = container
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
            
        # 创建容器实例
        container = cls()
            
        # 手动导入并注入依赖
        modules_to_inject = [
            "app.tasks.correction_tasks",
            "app.core.correction.correction_service"
        ]
        
        for module_name in modules_to_inject:
            try:
                # 尝试导入模块
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)
                
                # 为模块设置容器属性
                module.container = container
                logger.info(f"为工作进程中的模块 {module_name} 注入了依赖")
            except (ImportError, AttributeError) as e:
                logger.warning(f"无法为工作进程中的模块 {module_name} 注入依赖: {str(e)}")
        
        logger.info("服务容器已连接到Celery工作进程")

# 创建别名以保持向后兼容性
ServiceRegistry = ServiceContainer 