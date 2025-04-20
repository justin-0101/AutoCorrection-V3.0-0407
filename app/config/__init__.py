"""
配置包
包含应用的各种配置模块
"""

import os
import sys
import importlib.util

# 获取config.py文件的路径
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')

# 加载config.py模块
spec = importlib.util.spec_from_file_location('config_module', config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

# 从模块中导入需要的内容
Config = config_module.Config
load_config = config_module.load_config
config = config_module.config
config_dict = config_module.config

# 添加get_settings函数
def get_settings():
    """获取应用配置
    
    返回:
        dict: 包含应用配置的字典
    """
    config_name = os.environ.get('FLASK_ENV', 'default')
    if config_name == 'development':
        return config_module.DevelopmentConfig()
    elif config_name == 'testing':
        return config_module.TestingConfig()
    elif config_name == 'production':
        return config_module.ProductionConfig()
    else:
        return config_module.Config()

# 导出Celery配置
from app.config.celery_config import * 