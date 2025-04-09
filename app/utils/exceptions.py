#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异常处理工具模块
"""

import logging
from functools import wraps
from flask import jsonify, request, current_app

logger = logging.getLogger(__name__)

class APIError(Exception):
    """API错误基类"""
    status_code = 400
    
    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or {})
        rv['status'] = 'error'
        rv['message'] = self.message
        return rv

class ValidationError(APIError):
    """输入验证错误"""
    status_code = 400
    
    def __init__(self, message="输入数据验证失败", errors=None, status_code=None, payload=None):
        super().__init__(message, status_code, payload)
        self.errors = errors
    
    def to_dict(self):
        rv = super().to_dict()
        if self.errors:
            rv['errors'] = self.errors
        return rv

class AuthenticationError(APIError):
    """认证错误"""
    status_code = 401
    
    def __init__(self, message="认证失败", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class AuthorizationError(APIError):
    """授权错误"""
    status_code = 403
    
    def __init__(self, message="没有操作权限", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class ResourceNotFoundError(APIError):
    """资源不存在错误"""
    status_code = 404
    
    def __init__(self, message="请求的资源不存在", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class RateLimitError(APIError):
    """速率限制错误"""
    status_code = 429
    
    def __init__(self, message="请求过于频繁，请稍后再试", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class ServiceError(APIError):
    """服务错误"""
    status_code = 500
    
    def __init__(self, message="服务器内部错误", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class PaymentError(ServiceError):
    """支付错误"""
    status_code = 400 # Or 500 depending on context, using 400 for client-side payment issues like invalid method

    def __init__(self, message="支付处理失败", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class FileProcessError(ServiceError):
    """文件处理错误"""
    status_code = 500

    def __init__(self, message="文件处理失败", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class EmailError(ServiceError):
    """邮件发送错误"""
    status_code = 500

    def __init__(self, message="邮件发送失败", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class PermissionError(APIError):
    """权限错误"""
    status_code = 403
    
    def __init__(self, message="没有足够的权限执行此操作", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class QuotaExceededError(APIError):
    """配额超限错误"""
    status_code = 429
    
    def __init__(self, message="已超出使用配额限制", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class LimitExceededError(APIError):
    """限制超限错误"""
    status_code = 429
    
    def __init__(self, message="已超出限制", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

class ServiceUnavailableError(APIError):
    """服务不可用错误"""
    status_code = 503
    
    def __init__(self, message="服务暂时不可用", status_code=None, payload=None):
        super().__init__(message, status_code, payload)

def api_error_handler(f):
    """API错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            logger.warning(f"API错误: {e.message}, 状态码: {e.status_code}, 路径: {request.path}")
            response = jsonify(e.to_dict())
            response.status_code = e.status_code
            return response
        except Exception as e:
            logger.exception(f"未处理的异常: {str(e)}, 路径: {request.path}")
            if current_app.config.get('DEBUG'):
                # 在调试模式下返回详细错误信息
                response = jsonify({
                    'status': 'error',
                    'message': str(e),
                    'exception': e.__class__.__name__,
                    'path': request.path
                })
            else:
                # 在生产模式下返回通用错误信息
                response = jsonify({
                    'status': 'error',
                    'message': '服务器内部错误'
                })
            response.status_code = 500
            return response
    return decorated_function

def register_error_handlers(app):
    """注册全局错误处理器"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        logger.warning(f"API错误: {error.message}, 状态码: {error.status_code}")
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(404)
    def handle_not_found(error):
        logger.info(f"资源不存在: {request.path}")
        response = jsonify({
            'status': 'error',
            'message': '请求的资源不存在'
        })
        response.status_code = 404
        return response
    
    @app.errorhandler(500)
    def handle_server_error(error):
        logger.error(f"服务器错误: {str(error)}")
        response = jsonify({
            'status': 'error',
            'message': '服务器内部错误'
        })
        response.status_code = 500
        return response 