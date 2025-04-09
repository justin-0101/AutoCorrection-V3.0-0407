#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API错误处理模块
提供统一的异常处理机制，确保所有API错误返回一致的格式
"""

import logging
import traceback
from typing import Dict, Any, Optional, Type, List, Union
from functools import wraps

from flask import jsonify, request, current_app, Blueprint, g

from app.utils.exceptions import (
    APIError, ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, RateLimitError, ServiceError
)

logger = logging.getLogger(__name__)

class ErrorHandler:
    """API错误处理器"""
    
    _instance = None
    _initialized = False
    
    # 错误映射表，将Python异常映射到API错误
    _error_mappings = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorHandler, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not ErrorHandler._initialized:
            logger.info("初始化API错误处理器")
            self._default_status_code = 500
            self._log_exceptions = True
            self._include_traceback = False
            self._registered_blueprints = set()  # 添加一个集合来跟踪已注册的蓝图
            self._register_default_error_mappings()
            ErrorHandler._initialized = True
    
    def _register_default_error_mappings(self):
        """注册默认错误映射"""
        # Python内置异常
        self.register_error_mapping(ValueError, 400, "参数验证失败")
        self.register_error_mapping(TypeError, 400, "参数类型错误")
        self.register_error_mapping(KeyError, 400, "缺少必要参数")
        self.register_error_mapping(IndexError, 400, "索引越界")
        self.register_error_mapping(AttributeError, 500, "属性访问错误")
        self.register_error_mapping(AssertionError, 400, "断言失败")
        self.register_error_mapping(NotImplementedError, 501, "功能未实现")
        self.register_error_mapping(PermissionError, 403, "权限不足")
        self.register_error_mapping(FileNotFoundError, 404, "文件不存在")
        
        # 自定义API异常
        self.register_error_mapping(ValidationError, 422, "数据验证失败")
        self.register_error_mapping(AuthenticationError, 401, "未授权访问")
        self.register_error_mapping(AuthorizationError, 403, "禁止访问")
        self.register_error_mapping(ResourceNotFoundError, 404, "资源不存在")
        self.register_error_mapping(RateLimitError, 429, "请求过于频繁")
        self.register_error_mapping(ServiceError, 500, "服务器内部错误")
    
    def init_app(self, app, log_exceptions=True, include_traceback=False):
        """
        初始化错误处理器
        
        Args:
            app: Flask应用实例
            log_exceptions: 是否记录异常日志
            include_traceback: 是否在响应中包含堆栈跟踪信息（仅在DEBUG模式下生效）
        """
        self._log_exceptions = log_exceptions
        self._include_traceback = include_traceback
        
        # 注册错误处理器
        @app.errorhandler(Exception)
        def handle_exception(error):
            return self.handle_error(error)
        
        # 注册特定的HTTP错误处理器
        @app.errorhandler(400)
        def handle_bad_request(error):
            return self.handle_http_error(error, 400, "请求参数错误")
        
        @app.errorhandler(401)
        def handle_unauthorized(error):
            return self.handle_http_error(error, 401, "未授权访问")
        
        @app.errorhandler(403)
        def handle_forbidden(error):
            return self.handle_http_error(error, 403, "禁止访问")
        
        @app.errorhandler(404)
        def handle_not_found(error):
            return self.handle_http_error(error, 404, "资源不存在")
        
        @app.errorhandler(405)
        def handle_method_not_allowed(error):
            return self.handle_http_error(error, 405, "不支持的请求方法")
        
        @app.errorhandler(429)
        def handle_rate_limit(error):
            return self.handle_http_error(error, 429, "请求过于频繁")
        
        @app.errorhandler(500)
        def handle_server_error(error):
            return self.handle_http_error(error, 500, "服务器内部错误")
        
        logger.info("注册全局错误处理器完成")
    
    def register_blueprint_error_handlers(self, blueprint):
        """
        为蓝图注册错误处理器
        
        Args:
            blueprint: Flask蓝图实例
        """
        # 检查蓝图是否已经注册过错误处理器
        if blueprint.name in self._registered_blueprints:
            logger.debug(f"蓝图 {blueprint.name} 已经注册过错误处理器，跳过")
            return
            
        @blueprint.errorhandler(Exception)
        def handle_exception(error):
            return self.handle_error(error)
        
        # 记录已注册的蓝图
        self._registered_blueprints.add(blueprint.name)
        logger.info(f"为蓝图 {blueprint.name} 注册错误处理器完成")
    
    def register_error_mapping(self, exception_class, status_code, default_message=None):
        """
        注册异常映射
        
        Args:
            exception_class: 异常类
            status_code: HTTP状态码
            default_message: 默认错误消息
        """
        self._error_mappings[exception_class] = {
            'status_code': status_code,
            'message': default_message or str(exception_class.__name__)
        }
        logger.debug(f"注册错误映射: {exception_class.__name__} -> {status_code}")
    
    def get_error_mapping(self, exception):
        """
        获取异常映射
        
        Args:
            exception: 异常实例
            
        Returns:
            dict: 异常映射信息
        """
        # 首先尝试精确匹配异常类型
        if exception.__class__ in self._error_mappings:
            return self._error_mappings[exception.__class__]
        
        # 然后尝试匹配异常的父类
        for exception_class, mapping in self._error_mappings.items():
            if isinstance(exception, exception_class):
                return mapping
        
        # 默认映射
        return {
            'status_code': self._default_status_code,
            'message': "服务器内部错误"
        }
    
    def handle_error(self, exception):
        """
        处理异常
        
        Args:
            exception: 异常实例
            
        Returns:
            tuple: (response, status_code)
        """
        # 记录异常日志
        if self._log_exceptions:
            log_method = logger.exception if isinstance(exception, ServiceError) else logger.error
            log_method(f"处理异常: {str(exception)}")
        
        # 获取异常映射
        mapping = self.get_error_mapping(exception)
        status_code = mapping['status_code']
        message = str(exception) if str(exception) else mapping['message']
        
        # 构建错误响应
        response = {
            'status': 'error',
            'message': message
        }
        
        # 添加错误代码
        if hasattr(exception, 'code'):
            response['code'] = exception.code
        elif hasattr(exception, 'error_code'):
            response['code'] = exception.error_code
        
        # 添加详细错误信息
        if hasattr(exception, 'errors') and exception.errors:
            response['errors'] = exception.errors
        
        # 添加调试信息
        if current_app.config.get('DEBUG'):
            response['debug'] = {
                'exception_type': exception.__class__.__name__,
                'exception_args': [str(arg) for arg in exception.args],
                'path': request.path,
                'method': request.method
            }
            
            # 添加堆栈跟踪
            if self._include_traceback:
                response['debug']['traceback'] = traceback.format_exc()
        
        return jsonify(response), status_code
    
    def handle_http_error(self, error, status_code, default_message):
        """
        处理HTTP错误
        
        Args:
            error: HTTP错误对象
            status_code: HTTP状态码
            default_message: 默认错误消息
            
        Returns:
            tuple: (response, status_code)
        """
        message = str(error) if str(error) and str(error) != str(status_code) else default_message
        
        # 构建错误响应
        response = {
            'status': 'error',
            'message': message
        }
        
        # 添加调试信息
        if current_app.config.get('DEBUG'):
            response['debug'] = {
                'path': request.path,
                'method': request.method
            }
        
        return jsonify(response), status_code

# 创建错误处理器单例
error_handler = ErrorHandler()

def init_error_handler(app, log_exceptions=True, include_traceback=False):
    """
    初始化错误处理器
    
    Args:
        app: Flask应用实例
        log_exceptions: 是否记录异常日志
        include_traceback: 是否在响应中包含堆栈跟踪信息（仅在DEBUG模式下生效）
    """
    error_handler.init_app(app, log_exceptions, include_traceback)

def register_blueprint_error_handlers(blueprint):
    """
    为蓝图注册错误处理器
    
    Args:
        blueprint: Flask蓝图实例
    """
    error_handler.register_blueprint_error_handlers(blueprint)

def register_error_mapping(exception_class, status_code, default_message=None):
    """
    注册异常映射
    
    Args:
        exception_class: 异常类
        status_code: HTTP状态码
        default_message: 默认错误消息
    """
    error_handler.register_error_mapping(exception_class, status_code, default_message)

def api_error_handler(f):
    """
    API错误处理装饰器
    自动捕获函数执行过程中的异常，并将其转换为标准API错误响应
    
    Args:
        f: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            return error_handler.handle_error(e)
    return decorated_function 