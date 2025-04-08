#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型验证工具模块
提供模型字段验证和类型转换功能
"""

import logging
import re
import json
from typing import Any, Dict, List, Optional, Set, Type, Union, Callable
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from sqlalchemy import inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute

logger = logging.getLogger(__name__)

# 验证器类型
ValidatorFunc = Callable[[Any], Union[bool, tuple]]

class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")

# 基本验证器函数
def required(value: Any) -> bool:
    """验证字段是否有值"""
    if value is None:
        return False, "此字段不能为空"
    if isinstance(value, str) and value.strip() == '':
        return False, "此字段不能为空字符串"
    return True

def min_length(min_len: int) -> ValidatorFunc:
    """验证字符串最小长度"""
    def validator(value: Any) -> bool:
        if value is None:
            return True  # 如果字段允许为空，则跳过验证
        if not isinstance(value, str):
            return False, f"期望字符串类型，实际为{type(value).__name__}"
        if len(value) < min_len:
            return False, f"长度不能小于{min_len}个字符"
        return True
    return validator

def max_length(max_len: int) -> ValidatorFunc:
    """验证字符串最大长度"""
    def validator(value: Any) -> bool:
        if value is None:
            return True
        if not isinstance(value, str):
            return False, f"期望字符串类型，实际为{type(value).__name__}"
        if len(value) > max_len:
            return False, f"长度不能超过{max_len}个字符"
        return True
    return validator

def number_range(min_val: Optional[Union[int, float]] = None, max_val: Optional[Union[int, float]] = None) -> ValidatorFunc:
    """验证数字范围"""
    def validator(value: Any) -> bool:
        if value is None:
            return True
        if not isinstance(value, (int, float, Decimal)):
            return False, f"期望数字类型，实际为{type(value).__name__}"
        if min_val is not None and value < min_val:
            return False, f"不能小于{min_val}"
        if max_val is not None and value > max_val:
            return False, f"不能大于{max_val}"
        return True
    return validator

def email(value: Any) -> bool:
    """验证电子邮件格式"""
    if value is None:
        return True
    if not isinstance(value, str):
        return False, f"期望字符串类型，实际为{type(value).__name__}"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        return False, "邮箱格式不正确"
    return True

def url(value: Any) -> bool:
    """验证URL格式"""
    if value is None:
        return True
    if not isinstance(value, str):
        return False, f"期望字符串类型，实际为{type(value).__name__}"
    
    pattern = r'^(http|https)://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    if not re.match(pattern, value):
        return False, "URL格式不正确"
    return True

def phone(value: Any) -> bool:
    """验证手机号格式（中国大陆）"""
    if value is None:
        return True
    if not isinstance(value, str):
        return False, f"期望字符串类型，实际为{type(value).__name__}"
    
    pattern = r'^1[3-9]\d{9}$'
    if not re.match(pattern, value):
        return False, "手机号格式不正确"
    return True

def enum_member(enum_class: Type[Enum]) -> ValidatorFunc:
    """验证枚举值"""
    def validator(value: Any) -> bool:
        if value is None:
            return True
        
        # 如果是枚举实例
        if isinstance(value, enum_class):
            return True
        
        # 如果是枚举值
        try:
            enum_values = [e.value for e in enum_class]
            if value in enum_values:
                return True
        except (TypeError, AttributeError):
            pass
        
        # 如果是枚举名称
        try:
            enum_names = [e.name for e in enum_class]
            if value in enum_names:
                return True
        except (TypeError, AttributeError):
            pass
        
        return False, f"值必须是{enum_class.__name__}枚举的成员"
    return validator

def json_format(value: Any) -> bool:
    """验证JSON格式"""
    if value is None:
        return True
    
    # 如果已经是字典或列表，则视为有效
    if isinstance(value, (dict, list)):
        return True
    
    if not isinstance(value, str):
        return False, f"期望字符串或字典类型，实际为{type(value).__name__}"
    
    try:
        json.loads(value)
        return True
    except json.JSONDecodeError:
        return False, "JSON格式不正确"

def date_format(format_str: str = "%Y-%m-%d") -> ValidatorFunc:
    """验证日期格式"""
    def validator(value: Any) -> bool:
        if value is None:
            return True
        
        # 如果已经是日期或日期时间对象，则视为有效
        if isinstance(value, (date, datetime)):
            return True
        
        if not isinstance(value, str):
            return False, f"期望字符串类型，实际为{type(value).__name__}"
        
        try:
            datetime.strptime(value, format_str)
            return True
        except ValueError:
            return False, f"日期格式不正确，应为{format_str}"
    return validator

def datetime_format(format_str: str = "%Y-%m-%d %H:%M:%S") -> ValidatorFunc:
    """验证日期时间格式"""
    return date_format(format_str)

def regex(pattern: str, message: str = "格式不正确") -> ValidatorFunc:
    """使用正则表达式验证"""
    def validator(value: Any) -> bool:
        if value is None:
            return True
        if not isinstance(value, str):
            return False, f"期望字符串类型，实际为{type(value).__name__}"
        
        if not re.match(pattern, value):
            return False, message
        return True
    return validator

def choices(options: List[Any]) -> ValidatorFunc:
    """验证值是否在选项列表中"""
    def validator(value: Any) -> bool:
        if value is None:
            return True
        if value not in options:
            return False, f"值必须是以下选项之一: {', '.join(map(str, options))}"
        return True
    return validator

# 组合验证器
def and_validator(*validators: ValidatorFunc) -> ValidatorFunc:
    """组合多个验证器，所有验证器都必须通过"""
    def validator(value: Any) -> bool:
        for v in validators:
            result = v(value)
            if result is False or (isinstance(result, tuple) and not result[0]):
                return result
        return True
    return validator

def or_validator(*validators: ValidatorFunc) -> ValidatorFunc:
    """组合多个验证器，只需一个验证器通过即可"""
    def validator(value: Any) -> bool:
        errors = []
        for v in validators:
            result = v(value)
            if result is True or (isinstance(result, tuple) and result[0]):
                return True
            errors.append(result[1] if isinstance(result, tuple) else "验证失败")
        return False, " 或 ".join(errors)
    return validator

# 模型验证
class ModelValidator:
    """模型验证器类"""
    
    @staticmethod
    def validate_model(model: Any) -> Dict[str, List[str]]:
        """
        验证模型所有字段
        
        Args:
            model: 模型实例
            
        Returns:
            Dict[str, List[str]]: 字段错误信息
        """
        errors = {}
        
        # 获取模型类
        model_class = model.__class__
        
        # 获取模型验证规则
        validators = getattr(model_class, '__validators__', {})
        
        # 遍历所有字段
        for field_name, field in inspect(model_class).columns.items():
            field_value = getattr(model, field_name, None)
            
            # 应用字段验证器
            field_validators = validators.get(field_name, [])
            field_errors = []
            
            for validator in field_validators:
                result = validator(field_value)
                
                if result is False:
                    field_errors.append("验证失败")
                elif isinstance(result, tuple) and not result[0]:
                    field_errors.append(result[1])
            
            if field_errors:
                errors[field_name] = field_errors
        
        return errors
    
    @staticmethod
    def validate_field(model: Any, field_name: str, value: Any = None) -> List[str]:
        """
        验证模型单个字段
        
        Args:
            model: 模型实例
            field_name: 字段名
            value: 要验证的值，如果为None则使用模型当前值
            
        Returns:
            List[str]: 错误信息列表
        """
        # 获取模型类
        model_class = model.__class__
        
        # 获取模型验证规则
        validators = getattr(model_class, '__validators__', {})
        
        # 获取字段验证器
        field_validators = validators.get(field_name, [])
        
        # 如果没有提供值，使用模型当前值
        if value is None:
            value = getattr(model, field_name, None)
        
        # 应用验证器
        errors = []
        for validator in field_validators:
            result = validator(value)
            
            if result is False:
                errors.append("验证失败")
            elif isinstance(result, tuple) and not result[0]:
                errors.append(result[1])
        
        return errors
    
    @staticmethod
    def set_validators(model_class: Type, field_name: str, validators: List[ValidatorFunc]) -> None:
        """
        设置模型字段的验证器
        
        Args:
            model_class: 模型类
            field_name: 字段名
            validators: 验证器列表
        """
        # 确保模型类有__validators__属性
        if not hasattr(model_class, '__validators__'):
            model_class.__validators__ = {}
        
        # 设置字段的验证器
        model_class.__validators__[field_name] = validators

# 创建验证器字典的辅助函数
def create_validators(*validators: ValidatorFunc) -> List[ValidatorFunc]:
    """
    创建验证器列表
    
    Args:
        *validators: 验证器函数
        
    Returns:
        List[ValidatorFunc]: 验证器列表
    """
    return list(validators)

# 类型转换函数
def safe_convert(value: Any, target_type: Type, default: Any = None) -> Any:
    """
    安全地将值转换为目标类型
    
    Args:
        value: 要转换的值
        target_type: 目标类型
        default: 转换失败时的默认值
        
    Returns:
        Any: 转换后的值
    """
    if value is None:
        return default
    
    try:
        # 处理布尔值
        if target_type is bool:
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', 'y', '1', 'on')
            return bool(value)
        
        # 处理日期时间
        if target_type is datetime:
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    try:
                        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        return datetime.strptime(value, "%Y-%m-%d")
            return value
        
        # 处理日期
        if target_type is date:
            if isinstance(value, str):
                try:
                    return date.fromisoformat(value)
                except ValueError:
                    return datetime.strptime(value, "%Y-%m-%d").date()
            if isinstance(value, datetime):
                return value.date()
            return value
        
        # 处理字符串
        if target_type is str:
            return str(value)
        
        # 处理数字
        if target_type in (int, float, Decimal):
            if isinstance(value, str):
                value = value.strip()
            return target_type(value)
        
        # 处理列表和字典
        if target_type in (list, dict) and isinstance(value, str):
            return json.loads(value)
        
        # 其他类型直接转换
        return target_type(value)
    except (ValueError, TypeError, json.JSONDecodeError):
        logger.warning(f"转换值 {value} 到类型 {target_type.__name__} 失败，使用默认值 {default}")
        return default

# 验证模型函数
def validate_model(model: Any) -> Dict[str, List[str]]:
    """
    验证模型所有字段
    
    Args:
        model: 模型实例
        
    Returns:
        Dict[str, List[str]]: 字段错误信息
    """
    return ModelValidator.validate_model(model)

def validate_field(model: Any, field_name: str, value: Any = None) -> List[str]:
    """
    验证模型单个字段
    
    Args:
        model: 模型实例
        field_name: 字段名
        value: 要验证的值，如果为None则使用模型当前值
        
    Returns:
        List[str]: 错误信息列表
    """
    return ModelValidator.validate_field(model, field_name, value)

def set_validators(model_class: Type, field_name: str, validators: List[ValidatorFunc]) -> None:
    """
    设置模型字段的验证器
    
    Args:
        model_class: 模型类
        field_name: 字段名
        validators: 验证器列表
    """
    ModelValidator.set_validators(model_class, field_name, validators) 