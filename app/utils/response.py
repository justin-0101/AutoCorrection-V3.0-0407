#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
响应工具模块
提供统一的 API 响应格式
"""

from typing import Any, Dict, List, Optional, Union
from flask import jsonify

def success_response(
    data: Optional[Union[Dict[str, Any], List[Any]]] = None,
    message: str = "操作成功",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    生成成功响应
    
    Args:
        data: 响应数据
        message: 成功消息
        status_code: HTTP 状态码
        meta: 元数据，如分页信息
    
    Returns:
        包含响应数据的元组 (response, status_code)
    """
    response = {
        'status': 'success',
        'message': message
    }
    
    if data is not None:
        response['data'] = data
    
    if meta:
        response['meta'] = meta
    
    return jsonify(response), status_code

def error_response(
    message: str = "操作失败",
    status_code: int = 400,
    errors: Optional[Dict[str, List[str]]] = None,
    error_code: Optional[str] = None
) -> tuple:
    """
    生成错误响应
    
    Args:
        message: 错误消息
        status_code: HTTP 状态码
        errors: 详细错误信息
        error_code: 错误代码
    
    Returns:
        包含错误信息的元组 (response, status_code)
    """
    response = {
        'status': 'error',
        'message': message
    }
    
    if errors:
        response['errors'] = errors
    
    if error_code:
        response['error_code'] = error_code
    
    return jsonify(response), status_code

def pagination_meta(
    total: int,
    page: int,
    per_page: int,
    total_pages: Optional[int] = None
) -> Dict[str, Any]:
    """
    生成分页元数据
    
    Args:
        total: 总记录数
        page: 当前页码
        per_page: 每页记录数
        total_pages: 总页数（可选，如果不提供则自动计算）
    
    Returns:
        包含分页信息的字典
    """
    if total_pages is None:
        total_pages = (total + per_page - 1) // per_page
    
    return {
        'pagination': {
            'total': total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }

def list_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
    message: str = "获取列表成功",
    status_code: int = 200,
    extra_meta: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    生成列表响应
    
    Args:
        items: 列表数据
        total: 总记录数
        page: 当前页码
        per_page: 每页记录数
        message: 成功消息
        status_code: HTTP 状态码
        extra_meta: 额外的元数据
    
    Returns:
        包含列表数据和分页信息的元组 (response, status_code)
    """
    meta = pagination_meta(total, page, per_page)
    
    if extra_meta:
        meta.update(extra_meta)
    
    return success_response(
        data=items,
        message=message,
        status_code=status_code,
        meta=meta
    )

def created_response(
    data: Optional[Dict[str, Any]] = None,
    message: str = "创建成功",
    location: Optional[str] = None
) -> tuple:
    """
    生成资源创建成功响应
    
    Args:
        data: 创建的资源数据
        message: 成功消息
        location: 资源位置
    
    Returns:
        包含创建资源信息的元组 (response, status_code)
    """
    response = success_response(data, message, status_code=201)
    
    if location:
        response[0].headers['Location'] = location
    
    return response

def no_content_response() -> tuple:
    """
    生成无内容响应
    
    Returns:
        状态码为 204 的响应元组
    """
    return '', 204

def forbidden_response(
    message: str = "没有操作权限",
    error_code: Optional[str] = None
) -> tuple:
    """
    生成禁止访问响应
    
    Args:
        message: 错误消息
        error_code: 错误代码
    
    Returns:
        包含错误信息的元组 (response, status_code)
    """
    return error_response(message, status_code=403, error_code=error_code)

def not_found_response(
    message: str = "资源不存在",
    error_code: Optional[str] = None
) -> tuple:
    """
    生成资源不存在响应
    
    Args:
        message: 错误消息
        error_code: 错误代码
    
    Returns:
        包含错误信息的元组 (response, status_code)
    """
    return error_response(message, status_code=404, error_code=error_code)

def validation_error_response(
    message: str = "数据验证失败",
    errors: Optional[Dict[str, List[str]]] = None
) -> tuple:
    """
    生成数据验证错误响应
    
    Args:
        message: 错误消息
        errors: 验证错误详情
    
    Returns:
        包含验证错误信息的元组 (response, status_code)
    """
    return error_response(message, status_code=422, errors=errors)

def server_error_response(
    message: str = "服务器内部错误",
    error_code: Optional[str] = None
) -> tuple:
    """
    生成服务器错误响应
    
    Args:
        message: 错误消息
        error_code: 错误代码
    
    Returns:
        包含错误信息的元组 (response, status_code)
    """
    return error_response(message, status_code=500, error_code=error_code) 