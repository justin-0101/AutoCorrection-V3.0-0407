#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型工具模块
提供模型字段标准化和关系管理的工具函数
"""

import logging
import functools
from typing import List, Callable, Any, Dict, Optional, Type, Union
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, inspect
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)

def standardize_enum_field(field_value: Any, enum_class: Type[Enum], default_value=None) -> Union[str, Any]:
    """
    标准化枚举字段，确保一致的字符串表示形式
    
    Args:
        field_value: 字段值，可以是枚举实例、字符串或其他值
        enum_class: 枚举类
        default_value: 默认值，当转换失败时返回
        
    Returns:
        标准化后的字段值（通常是枚举值的字符串表示）
    """
    # 如果已经是枚举实例
    if isinstance(field_value, enum_class):
        return field_value.value
        
    # 如果是字符串，尝试转换为枚举值
    if isinstance(field_value, str):
        try:
            # 尝试通过名称匹配
            try:
                return enum_class[field_value].value
            except KeyError:
                # 尝试通过值匹配
                return enum_class(field_value).value
        except (ValueError, KeyError):
            logger.warning(f"无法将 '{field_value}' 转换为 {enum_class.__name__} 枚举值")
            return default_value if default_value is not None else field_value
    
    # 其他情况返回默认值
    return default_value if default_value is not None else field_value

def standardize_datetime(dt_value: Any) -> Optional[datetime]:
    """
    标准化日期时间字段
    
    Args:
        dt_value: 日期时间值，可以是字符串、时间戳或datetime对象
        
    Returns:
        标准化后的datetime对象，或None（如果转换失败）
    """
    if dt_value is None:
        return None
        
    # 如果已经是datetime对象
    if isinstance(dt_value, datetime):
        return dt_value
        
    # 如果是字符串，尝试解析
    if isinstance(dt_value, str):
        try:
            # 尝试多种常见格式
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO 8601 with microseconds and Z
                '%Y-%m-%dT%H:%M:%SZ',     # ISO 8601 without microseconds
                '%Y-%m-%dT%H:%M:%S.%f',   # ISO 8601 with microseconds
                '%Y-%m-%dT%H:%M:%S',      # ISO 8601 without microseconds
                '%Y-%m-%d %H:%M:%S.%f',   # Standard format with microseconds
                '%Y-%m-%d %H:%M:%S',      # Standard format without microseconds
                '%Y-%m-%d',               # Date only
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(dt_value, fmt)
                except ValueError:
                    continue
                    
            logger.warning(f"无法解析日期时间: {dt_value}")
            return None
        except Exception as e:
            logger.warning(f"日期时间解析错误: {str(e)}")
            return None
            
    # 如果是数字，假设是时间戳
    if isinstance(dt_value, (int, float)):
        try:
            return datetime.fromtimestamp(dt_value)
        except Exception as e:
            logger.warning(f"无法从时间戳转换: {str(e)}")
            return None
            
    return None

def standardize_boolean(bool_value: Any) -> bool:
    """
    标准化布尔字段
    
    Args:
        bool_value: 布尔值，可以是布尔类型、字符串或数字
        
    Returns:
        标准化后的布尔值
    """
    if bool_value is None:
        return False
        
    # 如果已经是布尔类型
    if isinstance(bool_value, bool):
        return bool_value
        
    # 如果是字符串
    if isinstance(bool_value, str):
        return bool_value.lower() in ('true', 'yes', 'y', '1', 'on')
        
    # 如果是数字
    if isinstance(bool_value, (int, float)):
        return bool_value != 0
        
    # 其他情况
    return bool(bool_value)

def cascade_relationship(back_populates: str = None, cascade: str = "all, delete-orphan", **kwargs) -> Callable:
    """
    创建带有标准级联选项的关系
    
    Args:
        back_populates: 关系另一端的属性名
        cascade: 级联选项
        **kwargs: 其他relationship参数
        
    Returns:
        配置好的relationship对象
    """
    if back_populates:
        kwargs['back_populates'] = back_populates
        
    return relationship(cascade=cascade, **kwargs)

def validate_model(model: Any) -> Dict[str, List[str]]:
    """
    验证模型数据
    
    Args:
        model: 数据模型实例
        
    Returns:
        Dict[str, List[str]]: 包含字段名和错误消息的字典
    """
    errors = {}
    
    # 获取模型的验证方法
    validators = {}
    for name in dir(model.__class__):
        attr = getattr(model.__class__, name)
        if hasattr(attr, '_validates_columns'):
            for column in attr._validates_columns:
                validators[column] = attr
    
    # 检查所有字段
    columns = inspect(model.__class__).columns
    for column in columns:
        column_name = column.name
        
        # 检查非空约束
        if not column.nullable and getattr(model, column_name) is None:
            errors.setdefault(column_name, []).append(f"{column_name} 不能为空")
            
        # 检查唯一约束
        if column.unique and getattr(model, column_name) is not None:
            # 这里只是标记可能的唯一性问题，实际验证需要查询数据库
            pass
            
        # 应用自定义验证器
        if column_name in validators:
            validator = validators[column_name]
            try:
                value = getattr(model, column_name)
                validated = validator(model, column_name, value)
                if validated != value and validated is not None:
                    setattr(model, column_name, validated)
            except ValueError as e:
                errors.setdefault(column_name, []).append(str(e))
    
    return errors

def validates_columns(*column_names: str) -> Callable:
    """
    标记一个方法验证指定的列
    
    Args:
        *column_names: 要验证的列名
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        func._validates_columns = column_names
        return func
    return decorator

def standard_dict_serializer(model: Any) -> Dict[str, Any]:
    """
    标准的模型序列化器
    
    Args:
        model: 数据模型实例
        
    Returns:
        Dict[str, Any]: 序列化后的字典
    """
    result = {}
    
    # 序列化普通列
    for column in inspect(model.__class__).columns:
        value = getattr(model, column.name)
        
        # 特殊类型处理
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Enum):
            value = value.value
            
        result[column.name] = value
    
    # 处理额外需要序列化的关系或属性
    if hasattr(model, '__dict_include__'):
        for name in model.__dict_include__:
            if hasattr(model, name):
                value = getattr(model, name)
                
                # 如果是一个可调用对象（方法或属性）
                if callable(value):
                    try:
                        value = value()
                    except:
                        continue
                
                # 处理关系对象
                if hasattr(value, 'to_dict'):
                    value = value.to_dict()
                    
                result[name] = value
    
    # 排除不需要序列化的字段
    if hasattr(model, '__dict_exclude__'):
        for name in model.__dict_exclude__:
            if name in result:
                del result[name]
    
    return result 