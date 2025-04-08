#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API装饰器模块
提供API请求验证和异常处理装饰器
"""

import logging
from functools import wraps
from typing import Dict, Any, Callable

from flask import request, jsonify

logger = logging.getLogger(__name__)


def validate_json(schema: Dict[str, type]) -> Callable:
    """
    验证请求JSON数据是否符合指定的模式
    
    Args:
        schema: 字段及其类型的字典, 例如: {"name": str, "age": int}
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 检查是否有JSON数据
            if not request.is_json:
                return jsonify({
                    "status": "error",
                    "message": "请求类型必须是JSON"
                }), 400
            
            data = request.get_json()
            if data is None:
                return jsonify({
                    "status": "error",
                    "message": "无法解析JSON数据"
                }), 400
            
            # 验证字段
            errors = []
            for field, field_type in schema.items():
                # 检查字段是否存在
                if field not in data:
                    errors.append(f"缺少必填字段: {field}")
                    continue
                
                # 检查字段类型
                if not isinstance(data[field], field_type):
                    errors.append(f"字段 {field} 类型必须是 {field_type.__name__}")
            
            if errors:
                return jsonify({
                    "status": "error",
                    "message": "数据验证失败",
                    "errors": errors
                }), 400
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def handle_exceptions(func: Callable) -> Callable:
    """
    异常处理装饰器，捕获并记录异常，返回友好的错误消息
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰器函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API异常: {func.__name__} - {str(e)}", exc_info=True)
            
            # 构造错误响应
            error_response = {
                "status": "error",
                "message": f"处理请求时发生错误: {str(e)}"
            }
            
            # 根据异常类型返回不同的HTTP状态码
            status_code = 500
            if isinstance(e, ValueError) or "validation" in str(e).lower():
                status_code = 400
            elif "not found" in str(e).lower() or "不存在" in str(e):
                status_code = 404
            elif "permission" in str(e).lower() or "unauthorized" in str(e).lower() or "权限" in str(e):
                status_code = 403
            
            return jsonify(error_response), status_code
    return wrapper


def rate_limit(limit: str) -> Callable:
    """
    速率限制装饰器(占位，实际实现需要使用Redis或其他存储)
    
    Args:
        limit: 限制表达式，如 "100/hour", "5/minute"
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 实际实现应该检查请求频率
            # 这里只是占位，实际项目中需要实现真正的速率限制
            return func(*args, **kwargs)
        return wrapper
    return decorator 