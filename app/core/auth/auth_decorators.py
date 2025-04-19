#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证装饰器
提供保护路由的装饰器函数
"""

import logging
from functools import wraps
from flask import request, g, jsonify, current_app, session, redirect, url_for
from flask_login import current_user

from app.core.auth.auth_service import AuthService

logger = logging.getLogger(__name__)

def get_token_from_request():
    """从请求中获取令牌"""
    # 首先从 Authorization 头部获取
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # 然后从查询参数获取
    token = request.args.get('token')
    if token:
        return token
    
    # 最后从表单数据获取
    return request.form.get('token')

def token_required(f):
    """
    验证API令牌的装饰器
    仅支持通过API令牌进行认证（不使用会话）
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取令牌
        token = get_token_from_request()
        if not token:
            logger.warning("缺少访问令牌")
            return jsonify({"status": "error", "message": "缺少访问令牌"}), 401
        
        # 验证令牌
        user = AuthService.verify_token(token)
        if not user:
            logger.warning("无效或已过期的令牌")
            return jsonify({"status": "error", "message": "无效或已过期的令牌"}), 401
        
        # 将用户信息存储在g中，以便后续使用
        g.user = user
        g.current_user = user  # 同时设置current_user，保持一致性
        return f(*args, **kwargs)
    
    return decorated_function

def login_required(f):
    """
    验证用户是否已登录的装饰器
    支持 Web 和 API 认证
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Web 认证：检查 Flask-Login 的登录状态
        if current_user.is_authenticated:
            # 同时设置g.user和g.current_user，保持一致性
            g.user = current_user._get_current_object()
            g.current_user = current_user._get_current_object()
            return f(*args, **kwargs)
        
        # API 认证：检查 JWT 令牌
        token = get_token_from_request()
        if token:
            user = AuthService.verify_token(token)
            if user:
                g.current_user = user
                g.user = user  # 同时设置g.user，保持一致性
                return f(*args, **kwargs)
        
        # 认证失败
        if request.is_json:
            logger.warning("API请求未认证")
            return jsonify({"status": "error", "message": "需要登录"}), 401
        return redirect(url_for('main.login', next=request.url))
    
    return decorated_function

def admin_required(f):
    """
    验证用户是否为管理员的装饰器
    支持 Web 和 API 认证
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Web 认证：检查 Flask-Login 的登录状态和管理员权限
        if not current_user.is_authenticated:
            if request.is_json:
                logger.warning("API请求未认证")
                return jsonify({"status": "error", "message": "需要登录"}), 401
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.is_admin:
            if request.is_json:
                logger.warning("非管理员API访问")
                return jsonify({"status": "error", "message": "需要管理员权限"}), 403
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def permission_required(permission_name):
    """
    要求用户具有特定权限的装饰器
    支持 Web 和 API 认证
    
    Args:
        permission_name: 所需的权限名称
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Web 认证：检查 Flask-Login 的登录状态
            if current_user.is_authenticated:
                if current_user.has_permission(permission_name):
                    return f(*args, **kwargs)
            else:
                # API 认证：检查 JWT 令牌
                token = get_token_from_request()
                if token:
                    user = AuthService.verify_token(token)
                    if user and user.has_permission(permission_name):
                        g.current_user = user
                        return f(*args, **kwargs)
            
            # 认证失败或无权限
            if request.is_json:
                logger.warning(f"用户无权限: {permission_name}")
                return jsonify({"status": "error", "message": f"需要 {permission_name} 权限"}), 403
            return redirect(url_for('main.index'))
        
        return decorated_function
    
    return decorator

def role_required(role_name):
    """
    要求用户具有特定角色的装饰器
    支持 Web 和 API 认证
    
    Args:
        role_name: 所需的角色名称
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Web 认证：检查 Flask-Login 的登录状态
            if current_user.is_authenticated:
                if current_user.has_role(role_name):
                    return f(*args, **kwargs)
            else:
                # API 认证：检查 JWT 令牌
                token = get_token_from_request()
                if token:
                    user = AuthService.verify_token(token)
                    if user and user.has_role(role_name):
                        g.current_user = user
                        return f(*args, **kwargs)
            
            # 认证失败或无权限
            if request.is_json:
                logger.warning(f"用户无角色: {role_name}")
                return jsonify({"status": "error", "message": f"需要 {role_name} 角色"}), 403
            return redirect(url_for('main.index'))
        
        return decorated_function
    
    return decorator 