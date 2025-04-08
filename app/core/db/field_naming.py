#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型字段命名规范模块
定义模型字段的命名规则和约定
"""

import logging
from typing import Dict, List, Tuple, Set
import re

logger = logging.getLogger(__name__)

# 字段前缀规则
PREFIX_RULES = {
    'boolean': {
        'required': ['is_'],  # 布尔值字段必须使用is_前缀
        'exceptions': ['active', 'enabled']  # 例外情况
    }
}

# 字段后缀规则
SUFFIX_RULES = {
    'id': {
        'required': ['_id'],  # ID字段必须使用_id后缀
        'exceptions': ['id']  # 例外情况（主键）
    },
    'datetime': {
        'preferred': ['_at'],  # 时间字段推荐使用_at后缀
        'exceptions': []
    }
}

# 标准字段名
STANDARD_FIELDS = {
    # 标识字段
    'id': {'type': 'Integer', 'nullable': False, 'primary_key': True},
    'uuid': {'type': 'String', 'nullable': False, 'unique': True},
    
    # 创建/更新时间
    'created_at': {'type': 'DateTime', 'nullable': False},
    'updated_at': {'type': 'DateTime', 'nullable': False},
    
    # 所有者/创建者字段
    'created_by_id': {'type': 'Integer', 'nullable': True},
    'updated_by_id': {'type': 'Integer', 'nullable': True},
    'owner_id': {'type': 'Integer', 'nullable': True},
    'user_id': {'type': 'Integer', 'nullable': True},
    
    # 常见状态字段
    'status': {'type': 'String', 'nullable': False},
    'is_active': {'type': 'Boolean', 'nullable': False, 'default': True},
    'is_deleted': {'type': 'Boolean', 'nullable': False, 'default': False},
    'is_default': {'type': 'Boolean', 'nullable': False, 'default': False},
    'is_public': {'type': 'Boolean', 'nullable': False, 'default': False},
    
    # 排序字段
    'order': {'type': 'Integer', 'nullable': False, 'default': 0},
    
    # 标签和分类
    'tags': {'type': 'JSON', 'nullable': True},
    'category': {'type': 'String', 'nullable': True},
    'type': {'type': 'String', 'nullable': True},
    
    # 版本控制
    'version': {'type': 'Integer', 'nullable': False, 'default': 1},
}

# 字段名称转换映射
# 用于旧字段名到新字段名的转换
FIELD_NAME_MAPPING = {
    # 示例：'old_field_name': 'new_field_name'
    'create_time': 'created_at',
    'update_time': 'updated_at',
    'createTime': 'created_at',
    'updateTime': 'updated_at',
    'create_date': 'created_at',
    'update_date': 'updated_at',
    'createDate': 'created_at',
    'updateDate': 'updated_at',
    
    'is_activated': 'is_active',
    'active': 'is_active',
    'enabled': 'is_active',
    'is_enabled': 'is_active',
    
    'deleted': 'is_deleted',
    
    'creator_id': 'created_by_id',
    'updater_id': 'updated_by_id',
}

def check_field_naming(field_name: str, field_type: str) -> Tuple[bool, str]:
    """
    检查字段命名是否符合规范
    
    Args:
        field_name: 字段名
        field_type: 字段类型
        
    Returns:
        Tuple[bool, str]: (是否符合规范, 推荐名称或错误信息)
    """
    # 检查标准字段
    if field_name in STANDARD_FIELDS:
        return True, field_name
        
    # 检查字段映射
    if field_name in FIELD_NAME_MAPPING:
        recommended = FIELD_NAME_MAPPING[field_name]
        return False, f"应使用标准字段名: {recommended}"
        
    # 布尔字段前缀检查
    if field_type.lower() == 'boolean':
        rules = PREFIX_RULES.get('boolean', {})
        required_prefix = rules.get('required', [])[0] if rules.get('required') else None
        exceptions = rules.get('exceptions', [])
        
        if required_prefix and not field_name.startswith(required_prefix) and field_name not in exceptions:
            recommended = f"{required_prefix}{field_name}"
            return False, f"布尔字段应以 '{required_prefix}' 开头，推荐: {recommended}"
            
    # ID字段后缀检查
    if field_name.endswith('id') and not field_name.endswith('_id') and field_name != 'id':
        recommended = re.sub(r'id$', '_id', field_name)
        return False, f"ID字段应以 '_id' 结尾，推荐: {recommended}"
        
    # 日期时间字段后缀检查
    if field_type.lower() == 'datetime' and not field_name.endswith('_at') and not field_name.endswith('_date'):
        recommended = f"{field_name}_at"
        return False, f"日期时间字段推荐以 '_at' 结尾，推荐: {recommended}"
        
    # 默认符合规范
    return True, field_name

def get_standard_fields() -> Dict[str, Dict]:
    """
    获取标准字段定义
    
    Returns:
        Dict[str, Dict]: 标准字段定义
    """
    return STANDARD_FIELDS

def get_field_naming_suggestions(model_class) -> List[Dict[str, str]]:
    """
    获取模型字段命名建议
    
    Args:
        model_class: 模型类
        
    Returns:
        List[Dict[str, str]]: 字段命名建议列表
    """
    suggestions = []
    
    # 检查每个字段
    for column in model_class.__table__.columns:
        field_name = column.name
        field_type = column.type.__class__.__name__
        
        is_valid, message = check_field_naming(field_name, field_type)
        if not is_valid:
            suggestions.append({
                'field_name': field_name,
                'field_type': field_type,
                'suggestion': message
            })
            
    return suggestions

def get_renamed_fields(model_class) -> Dict[str, str]:
    """
    获取需要重命名的字段
    
    Args:
        model_class: 模型类
        
    Returns:
        Dict[str, str]: 旧字段名到新字段名的映射
    """
    rename_map = {}
    
    # 检查每个字段
    for column in model_class.__table__.columns:
        field_name = column.name
        field_type = column.type.__class__.__name__
        
        is_valid, message = check_field_naming(field_name, field_type)
        if not is_valid and field_name in FIELD_NAME_MAPPING:
            rename_map[field_name] = FIELD_NAME_MAPPING[field_name]
            
    return rename_map 