#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
来源类型管理模块
提供灵活的来源类型管理和配置功能
"""

import logging
import os
import json
import yaml
from enum import Enum
from app.utils.input_sanitizer import sanitize_input

logger = logging.getLogger(__name__)

class SourceTypeManager:
    """
    来源类型管理类
    支持动态注册、配置加载和类型验证
    """
    _instance = None
    _types = set()  # 默认支持的类型
    _type_config = {
        'validation': {
            'case_sensitive': False,
            'allow_whitespace': False,
            'max_length': 20
        },
        'defaults': {
            'default_type': 'text',
            'fallback_type': 'text'
        }
    }
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(SourceTypeManager, cls).__new__(cls)
            # 初始化默认类型
            cls._types = {'text', 'paste', 'upload', 'api'}
        return cls._instance
    
    @classmethod
    def register_type(cls, name):
        """
        注册新的来源类型
        
        参数:
            name: 来源类型名称
        
        返回:
            成功注册返回True，否则返回False
        """
        if not name or not isinstance(name, str):
            logger.warning(f"无法注册无效的来源类型: {name}")
            return False
            
        sanitized_name = sanitize_input(
            name,
            max_length=cls._type_config['validation']['max_length'],
            allow_whitespace=cls._type_config['validation']['allow_whitespace'],
            lowercase=not cls._type_config['validation']['case_sensitive']
        )
        
        if not sanitized_name:
            logger.warning(f"清理后的来源类型为空，无法注册: {name}")
            return False
            
        if sanitized_name in cls._types:
            logger.info(f"来源类型 '{sanitized_name}' 已存在，跳过注册")
            return True
            
        cls._types.add(sanitized_name)
        logger.info(f"成功注册来源类型: '{sanitized_name}'")
        return True
    
    @classmethod
    def unregister_type(cls, name):
        """
        取消注册来源类型
        
        参数:
            name: 来源类型名称
            
        返回:
            成功取消注册返回True，否则返回False
        """
        # 不能删除默认类型
        if name == cls._type_config['defaults']['default_type']:
            logger.warning(f"无法删除默认类型: {name}")
            return False
            
        # 清理名称
        sanitized_name = sanitize_input(
            name,
            max_length=cls._type_config['validation']['max_length'],
            allow_whitespace=cls._type_config['validation']['allow_whitespace'],
            lowercase=not cls._type_config['validation']['case_sensitive']
        )
        
        if sanitized_name in cls._types:
            cls._types.remove(sanitized_name)
            logger.info(f"成功取消注册来源类型: '{sanitized_name}'")
            return True
        
        logger.warning(f"来源类型 '{sanitized_name}' 不存在，无法取消注册")
        return False
    
    @classmethod
    def get_types(cls):
        """
        获取所有注册的类型
        
        返回:
            类型集合的副本
        """
        return cls._types.copy()
    
    @classmethod
    def is_valid_type(cls, source_type):
        """
        验证来源类型是否有效
        
        参数:
            source_type: 要验证的来源类型
            
        返回:
            有效返回True，否则返回False
        """
        if not source_type:
            return False
            
        # 清理并验证
        sanitized_type = sanitize_input(
            source_type,
            max_length=cls._type_config['validation']['max_length'],
            allow_whitespace=cls._type_config['validation']['allow_whitespace'],
            lowercase=not cls._type_config['validation']['case_sensitive']
        )
        
        return sanitized_type in cls._types
    
    @classmethod
    def get_default_type(cls):
        """
        获取默认类型
        
        返回:
            默认类型名称
        """
        return cls._type_config['defaults']['default_type']
    
    @classmethod
    def normalize_type(cls, source_type):
        """
        标准化来源类型
        
        参数:
            source_type: 输入的来源类型
            
        返回:
            标准化后的来源类型，如果无效则返回默认类型
        """
        if not source_type:
            return cls._type_config['defaults']['default_type']
            
        # 清理输入
        sanitized_type = sanitize_input(
            source_type,
            max_length=cls._type_config['validation']['max_length'],
            allow_whitespace=cls._type_config['validation']['allow_whitespace'],
            lowercase=not cls._type_config['validation']['case_sensitive']
        )
        
        # 验证并返回
        if sanitized_type in cls._types:
            return sanitized_type
        
        # 模糊匹配
        for type_name in cls._types:
            if type_name in sanitized_type or sanitized_type in type_name:
                logger.info(f"模糊匹配 '{sanitized_type}' -> '{type_name}'")
                return type_name
                
        return cls._type_config['defaults']['fallback_type']
    
    @classmethod
    def load_config(cls, config_path=None):
        """
        从配置文件加载类型配置
        
        参数:
            config_path: 配置文件路径，默认为None（使用默认路径）
            
        返回:
            加载成功返回True，否则返回False
        """
        # 默认配置路径
        if config_path is None:
            # 尝试多个可能的位置
            possible_paths = [
                'config/source_types.yaml',
                'config/source_types.yml',
                'config/source_types.json',
                'app/config/source_types.yaml',
                'app/config/source_types.yml',
                'app/config/source_types.json'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if not config_path or not os.path.exists(config_path):
            logger.warning(f"找不到配置文件: {config_path}")
            return False
            
        try:
            ext = os.path.splitext(config_path)[1].lower()
            with open(config_path, 'r', encoding='utf-8') as f:
                if ext in ('.yaml', '.yml'):
                    config = yaml.safe_load(f)
                elif ext == '.json':
                    config = json.load(f)
                else:
                    logger.error(f"不支持的配置文件格式: {ext}")
                    return False
                    
            # 更新配置
            if 'validation' in config:
                cls._type_config['validation'].update(config['validation'])
                
            if 'defaults' in config:
                cls._type_config['defaults'].update(config['defaults'])
                
            # 加载类型
            if 'allowed_types' in config and isinstance(config['allowed_types'], list):
                # 清空现有类型并重新加载
                if config.get('replace_types', False):
                    cls._types = set()
                
                # 加载配置中的类型
                for type_name in config['allowed_types']:
                    cls.register_type(type_name)
                    
            logger.info(f"已从 {config_path} 加载类型配置")
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return False
            
    @classmethod
    def create_enum_class(cls):
        """
        创建表示所有注册类型的枚举类
        
        返回:
            动态创建的枚举类
        """
        enum_items = {
            name.upper() if not cls._type_config['validation']['case_sensitive'] else name: 
            name for name in cls._types
        }
        
        # 创建动态枚举类
        DynamicSourceType = Enum('DynamicSourceType', enum_items)
        
        # 添加一些有用的方法
        def get_display_name(self):
            """返回显示名称"""
            display_names = {
                'text': '文本输入',
                'upload': '文件上传',
                'paste': '文本粘贴',
                'api': 'API提交'
            }
            return display_names.get(self.value, self.value)
            
        DynamicSourceType.display_name = property(get_display_name)
        
        return DynamicSourceType

# 示例配置文件内容
DEFAULT_CONFIG = """
# config/source_types.yaml
allowed_types:
  - text
  - paste
  - upload
  - api
  - email  # 可添加新的类型
  - speech # 语音输入
validation:
  case_sensitive: false
  allow_whitespace: false
  max_length: 20
defaults:
  default_type: text
  fallback_type: text
replace_types: false  # 是否替换现有类型
"""

def create_default_config(config_dir='config'):
    """
    创建默认配置文件
    
    参数:
        config_dir: 配置目录
    
    返回:
        创建成功返回True，否则返回False
    """
    try:
        # 确保目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        config_path = os.path.join(config_dir, 'source_types.yaml')
        
        # 检查文件是否已存在
        if os.path.exists(config_path):
            logger.info(f"配置文件已存在: {config_path}")
            return True
            
        # 写入默认配置
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_CONFIG)
            
        logger.info(f"已创建默认配置文件: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"创建默认配置文件失败: {str(e)}")
        return False

# 初始化
def init_source_types():
    """初始化来源类型系统"""
    try:
        # 创建默认配置（如果不存在）
        create_default_config()
        
        # 加载配置
        SourceTypeManager.load_config()
        
        logger.info(f"来源类型系统已初始化，可用类型: {', '.join(SourceTypeManager.get_types())}")
        return True
    except Exception as e:
        logger.error(f"初始化来源类型系统失败: {str(e)}")
        return False 