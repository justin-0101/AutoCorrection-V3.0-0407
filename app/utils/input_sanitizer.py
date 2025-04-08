#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
输入处理工具模块
提供各种输入处理和清理函数
"""

import re
import logging
from unicodedata import normalize
from typing import Optional, Union, Any

logger = logging.getLogger(__name__)

def sanitize_input(value: Any, max_length: int = 50, default: str = '', 
                  allow_whitespace: bool = True, lowercase: bool = True,
                  enum_values: Optional[list] = None) -> str:
    """
    标准化字符串输入
    
    参数:
        value: 要清理的输入值，可以是任何类型
        max_length: 最大长度限制
        default: 当值无效时返回的默认值
        allow_whitespace: 是否保留空白字符
        lowercase: 是否转换为小写
        enum_values: 有效的枚举值列表，如果提供，将验证清理后的字符串是否匹配
    
    返回:
        清理后的字符串
    """
    if value is None:
        logger.debug(f"收到空值，返回默认值: '{default}'")
        return default
    
    # 转换为字符串
    try:
        if not isinstance(value, str):
            cleaned = str(value)
            logger.debug(f"非字符串输入已转换: {type(value)} -> 字符串")
        else:
            cleaned = value
    except Exception as e:
        logger.warning(f"字符串转换异常: {str(e)}，返回默认值")
        return default
    
    # 记录原始输入
    original = cleaned
    logger.debug(f"原始输入: '{original}'")
    
    # 字符码点分析（调试用）
    try:
        codepoints = ' '.join([f'U+{ord(c):04X}' for c in cleaned])
        logger.debug(f"字符码点分析: {codepoints}")
    except Exception:
        pass
    
    # 统一Unicode格式（NFKC同时进行兼容性分解和标准组合）
    try:
        cleaned = normalize('NFKC', cleaned)
    except Exception as e:
        logger.warning(f"Unicode标准化异常: {str(e)}")
    
    # 去除/保留空白字符
    if allow_whitespace:
        cleaned = cleaned.strip()
    else:
        cleaned = re.sub(r'\s', '', cleaned)
    
    # 去除控制字符
    cleaned = ''.join(c for c in cleaned if c.isprintable())
    
    # 转为小写（如果需要）
    if lowercase:
        cleaned = cleaned.lower()
    
    # 长度限制
    if max_length and len(cleaned) > max_length:
        logger.warning(f"输入超过长度限制({max_length})，已截断")
        cleaned = cleaned[:max_length]
    
    # 检查清理后的结果是否为空
    if not cleaned:
        logger.debug(f"清理后为空值，返回默认值: '{default}'")
        return default
    
    # 枚举值验证
    if enum_values:
        if cleaned not in enum_values:
            closest = next((v for v in enum_values if v in cleaned or cleaned in v), None)
            if closest:
                logger.warning(f"值'{cleaned}'不完全匹配枚举值，已匹配到最接近的值: '{closest}'")
                return closest
            logger.warning(f"值'{cleaned}'不在有效枚举值列表中，返回默认值: '{default}'")
            return default
    
    logger.debug(f"清理结果: '{cleaned}'")
    return cleaned

def sanitize_enum_input(value: Any, enum_class, default=None):
    """
    处理枚举类型的输入
    
    参数:
        value: 输入值
        enum_class: 枚举类
        default: 默认枚举值
    
    返回:
        匹配的枚举值或默认值
    """
    if value is None:
        return default
    
    # 如果已经是枚举实例，直接返回
    if isinstance(value, enum_class):
        return value
    
    # 获取所有有效的枚举值
    enum_values = [e.value for e in enum_class]
    enum_names = [e.name for e in enum_class]
    
    # 标准化输入并尝试匹配枚举值
    cleaned_value = sanitize_input(value, enum_values=enum_values)
    
    # 尝试按值匹配
    for enum_item in enum_class:
        if enum_item.value == cleaned_value:
            return enum_item
    
    # 尝试按名称匹配
    try:
        if isinstance(value, str) and value.upper() in enum_names:
            return enum_class[value.upper()]
    except (KeyError, ValueError):
        pass
    
    # 返回默认值
    return default 