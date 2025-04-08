#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API响应格式化模块
确保所有API响应遵循统一格式
"""

import logging
import functools
import json
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from flask import jsonify, Response, make_response, g, request, current_app

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """API响应格式化器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResponseFormatter, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not ResponseFormatter._initialized:
            logger.info("初始化API响应格式化器")
            self._enabled = True
            self._api_prefixes = ['/api']
            self._excluded_paths = []
            ResponseFormatter._initialized = True
    
    def init_app(self, app, api_prefixes=None, excluded_paths=None):
        """
        初始化响应格式化器
        
        Args:
            app: Flask应用实例
            api_prefixes: API前缀列表，默认为['/api']
            excluded_paths: 排除的路径列表，这些路径不会被格式化
        """
        if api_prefixes:
            self._api_prefixes = api_prefixes
        
        if excluded_paths:
            self._excluded_paths = excluded_paths
        
        # 注册响应处理钩子
        @app.after_request
        def format_response(response):
            return self.process_response(response)
        
        # 注册配置变更处理器
        @app.before_request
        def check_formatter_config():
            # 可以在这里实现根据请求动态启用或禁用格式化器
            pass
    
    def is_api_request(self, path):
        """
        检查请求路径是否为API请求
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否为API请求
        """
        return any(path.startswith(prefix) for prefix in self._api_prefixes)
    
    def should_format_response(self, response, path):
        """
        检查是否应该格式化响应
        
        Args:
            response: Flask响应对象
            path: 请求路径
            
        Returns:
            bool: 是否应该格式化响应
        """
        # 检查是否启用格式化器
        if not self._enabled:
            return False
        
        # 检查是否为API请求
        if not self.is_api_request(path):
            return False
        
        # 检查是否在排除列表中
        if any(path.startswith(excluded) for excluded in self._excluded_paths):
            return False
        
        # 检查响应类型
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            return False
        
        # 检查状态码，某些状态码可能需要特殊处理
        if response.status_code == 204:  # No Content
            return False
        
        return True
    
    def process_response(self, response):
        """
        处理响应，确保符合标准格式
        
        Args:
            response: Flask响应对象
            
        Returns:
            Response: 格式化后的响应
        """
        path = request.path
        
        # 检查是否需要格式化
        if not self.should_format_response(response, path):
            return response
        
        try:
            # 解析原始响应数据
            data = json.loads(response.get_data(as_text=True))
            
            # 如果响应已经符合标准格式，则不需要额外处理
            if isinstance(data, dict) and 'status' in data:
                return response
            
            # 构建标准响应格式
            status_code = response.status_code
            is_success = 200 <= status_code < 300
            
            standard_response = {
                'status': 'success' if is_success else 'error',
                'message': self._get_default_message(status_code),
            }
            
            # 添加数据
            if is_success:
                standard_response['data'] = data
            else:
                # 错误响应
                if isinstance(data, dict) and 'message' in data:
                    standard_response['message'] = data['message']
                
                # 添加错误详情
                if isinstance(data, dict) and 'errors' in data:
                    standard_response['errors'] = data['errors']
                
                # 添加错误代码
                if isinstance(data, dict) and 'code' in data:
                    standard_response['code'] = data['code']
                elif isinstance(data, dict) and 'error_code' in data:
                    standard_response['code'] = data['error_code']
                
                # 添加请求信息用于调试
                if current_app.config.get('DEBUG'):
                    standard_response['request'] = {
                        'path': request.path,
                        'method': request.method
                    }
            
            # 创建新的响应
            new_response = make_response(jsonify(standard_response), status_code)
            
            # 复制原始响应的头信息
            for key, value in response.headers.items():
                if key.lower() != 'content-length':  # 内容长度会自动计算
                    new_response.headers[key] = value
            
            return new_response
            
        except Exception as e:
            logger.exception(f"格式化响应时出错: {str(e)}")
            return response
    
    def _get_default_message(self, status_code):
        """
        根据状态码获取默认消息
        
        Args:
            status_code: HTTP状态码
            
        Returns:
            str: 默认消息
        """
        status_messages = {
            200: "操作成功",
            201: "创建成功",
            400: "请求参数错误",
            401: "未授权访问",
            403: "禁止访问",
            404: "资源不存在",
            405: "不支持的请求方法",
            409: "资源冲突",
            422: "数据验证失败",
            429: "请求过于频繁",
            500: "服务器内部错误"
        }
        
        return status_messages.get(status_code, "未知状态")
    
    def enable(self):
        """启用响应格式化器"""
        self._enabled = True
    
    def disable(self):
        """禁用响应格式化器"""
        self._enabled = False
    
    def add_api_prefix(self, prefix):
        """
        添加API前缀
        
        Args:
            prefix: API前缀
        """
        if prefix not in self._api_prefixes:
            self._api_prefixes.append(prefix)
    
    def add_excluded_path(self, path):
        """
        添加排除路径
        
        Args:
            path: 排除路径
        """
        if path not in self._excluded_paths:
            self._excluded_paths.append(path)

# 创建响应格式化器单例
response_formatter = ResponseFormatter()

def init_response_formatter(app, api_prefixes=None, excluded_paths=None):
    """
    初始化响应格式化器
    
    Args:
        app: Flask应用实例
        api_prefixes: API前缀列表，默认为['/api']
        excluded_paths: 排除的路径列表，这些路径不会被格式化
    """
    response_formatter.init_app(app, api_prefixes, excluded_paths)

def format_api_response(data=None, message=None, status_code=200, meta=None, errors=None, error_code=None):
    """
    生成标准API响应
    
    Args:
        data: 响应数据
        message: 响应消息
        status_code: HTTP状态码
        meta: 元数据
        errors: 错误详情
        error_code: 错误代码
        
    Returns:
        tuple: (response, status_code)
    """
    is_success = 200 <= status_code < 300
    
    if message is None:
        message = response_formatter._get_default_message(status_code)
    
    response = {
        'status': 'success' if is_success else 'error',
        'message': message
    }
    
    if is_success and data is not None:
        response['data'] = data
    
    if meta is not None:
        response['meta'] = meta
    
    if not is_success and errors is not None:
        response['errors'] = errors
    
    if not is_success and error_code is not None:
        response['code'] = error_code
    
    return jsonify(response), status_code

def api_response(func=None, *, default_message=None, default_status_code=200):
    """
    API响应装饰器，确保函数返回标准格式的API响应
    
    使用方式:
    @api_response
    def my_api_function():
        return data
        
    或
    
    @api_response(default_message="自定义默认消息", default_status_code=201)
    def my_api_function():
        return data
    
    Args:
        func: 被装饰的函数
        default_message: 默认响应消息
        default_status_code: 默认HTTP状态码
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # 如果函数返回的已经是一个元组 (response, status_code)，则不需要额外处理
            if isinstance(result, tuple) and len(result) >= 2:
                return result
            
            # 如果函数返回的是Response对象，则直接返回
            if isinstance(result, Response):
                return result
            
            # 否则，将结果包装为标准格式的API响应
            message = default_message or response_formatter._get_default_message(default_status_code)
            return format_api_response(data=result, message=message, status_code=default_status_code)
        
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func) 