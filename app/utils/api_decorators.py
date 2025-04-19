#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 装饰器工具模块
"""

import logging
from functools import wraps
from flask import jsonify, request, current_app, g
from app.utils.exceptions import APIError, ValidationError, AuthenticationError
from flask_login import current_user

logger = logging.getLogger(__name__)

def api_error_handler(f):
    """API 错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # 确保用户对象的一致性
            if hasattr(g, 'current_user') and not hasattr(g, 'user'):
                g.user = g.current_user
            elif hasattr(g, 'user') and not hasattr(g, 'current_user'):
                g.current_user = g.user
                
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

def validate_json_payload(*required_fields):
    """验证 JSON 请求体装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise ValidationError('请求必须是 JSON 格式')
            
            data = request.get_json()
            if not data:
                raise ValidationError('请求体不能为空')
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(f'缺少必要的字段: {", ".join(missing_fields)}')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_query_params(*required_params):
    """验证查询参数装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            missing_params = [param for param in required_params if param not in request.args]
            if missing_params:
                raise ValidationError(f'缺少必要的查询参数: {", ".join(missing_params)}')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def rate_limit(limit=100, per=60):
    """速率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端 IP
            client_ip = request.remote_addr
            
            # 获取当前时间窗口内的请求次数
            current_count = current_app.redis.get(f'rate_limit:{client_ip}')
            if current_count and int(current_count) >= limit:
                raise APIError('请求过于频繁，请稍后再试', status_code=429)
            
            # 更新请求计数
            if not current_count:
                current_app.redis.setex(f'rate_limit:{client_ip}', per, 1)
            else:
                current_app.redis.incr(f'rate_limit:{client_ip}')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def cache_response(timeout=300):
    """缓存响应装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            cache_key = f'cache:{request.path}:{request.query_string.decode()}'
            
            # 尝试从缓存获取响应
            cached_response = current_app.redis.get(cache_key)
            if cached_response:
                return jsonify(eval(cached_response))
            
            # 执行原始函数
            response = f(*args, **kwargs)
            
            # 缓存响应
            if response.status_code == 200:
                current_app.redis.setex(
                    cache_key,
                    timeout,
                    str(response.get_json())
                )
            
            return response
        return decorated_function
    return decorator

def log_request(f):
    """请求日志装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 记录请求信息
        logger.info(f"请求方法: {request.method}")
        logger.info(f"请求路径: {request.path}")
        logger.info(f"请求参数: {dict(request.args)}")
        logger.info(f"请求头: {dict(request.headers)}")
        
        if request.is_json:
            logger.info(f"请求体: {request.get_json()}")
        
        # 执行原始函数
        response = f(*args, **kwargs)
        
        # 记录响应信息
        logger.info(f"响应状态码: {response.status_code}")
        logger.info(f"响应数据: {response.get_json()}")
        
        return response
    return decorated_function

def validate_file_upload(allowed_extensions=None, max_size=None):
    """验证文件上传装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'file' not in request.files:
                raise ValidationError('没有上传文件')
            
            file = request.files['file']
            if not file.filename:
                raise ValidationError('没有选择文件')
            
            # 验证文件扩展名
            if allowed_extensions:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if ext not in allowed_extensions:
                    raise ValidationError(f'不支持的文件类型，允许的类型：{", ".join(allowed_extensions)}')
            
            # 验证文件大小
            if max_size and request.content_length > max_size:
                max_size_mb = max_size / (1024 * 1024)
                raise ValidationError(f'文件大小超过限制，最大允许：{max_size_mb}MB')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_api_key(f):
    """API 密钥验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            raise AuthenticationError('缺少 API 密钥')
        
        # 验证 API 密钥
        if api_key != current_app.config.get('API_KEY'):
            raise AuthenticationError('无效的 API 密钥')
        
        return f(*args, **kwargs)
    return decorated_function

def user_compatibility(f):
    """确保g.user和g.current_user的兼容性装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 如果flask_login的current_user已认证，优先使用它
        if current_user.is_authenticated:
            user_obj = current_user._get_current_object()
            g.user = user_obj
            g.current_user = user_obj
        # 否则检查g对象中是否已经存在用户信息
        elif hasattr(g, 'current_user') and not hasattr(g, 'user'):
            g.user = g.current_user
        elif hasattr(g, 'user') and not hasattr(g, 'current_user'):
            g.current_user = g.user
            
        return f(*args, **kwargs)
    return decorated_function

# 更新现有的API路由装饰器，使其包含用户兼容性
def api_route_auth(f):
    """API路由认证装饰器，结合了错误处理和用户兼容性"""
    @wraps(f)
    @api_error_handler
    @user_compatibility
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function 