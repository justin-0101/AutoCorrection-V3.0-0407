#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
权限管理模块
提供统一的权限检查机制，支持基于角色的权限控制和基于资源的权限控制
"""

import logging
import functools
from typing import Callable, Dict, List, Optional, Union, Any
from flask import g, request, jsonify, redirect, url_for, current_app
from flask_login import current_user

from app.utils.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

class PermissionManager:
    """权限管理器类"""
    
    _instance = None
    _initialized = False
    
    # 权限缓存，用于提高性能
    _permission_cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PermissionManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not PermissionManager._initialized:
            logger.info("初始化权限管理器")
            self._auth_service = None
            self._permission_definitions = {}
            PermissionManager._initialized = True
    
    def init_app(self, app, auth_service=None):
        """
        初始化权限管理器
        
        Args:
            app: Flask应用实例
            auth_service: 认证服务实例，如果为None则尝试在运行时获取
        """
        self._auth_service = auth_service
        
        # 注册权限检查钩子
        @app.before_request
        def check_permissions():
            # 权限前置检查可以在这里实现
            pass
    
    def get_auth_service(self):
        """获取认证服务实例"""
        if self._auth_service is None:
            # 动态获取认证服务，避免循环导入
            try:
                from app.core.auth.auth_service import AuthService
                self._auth_service = AuthService()
            except ImportError:
                logger.error("无法导入AuthService，权限检查可能无法正常工作")
                return None
        return self._auth_service
    
    def get_current_user(self):
        """获取当前用户，支持多种认证方式"""
        # 首先检查Flask-Login的current_user
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            return current_user
        
        # 然后检查g对象中是否已存储了认证用户
        user = getattr(g, 'current_user', None)
        if user:
            return user
        
        # 最后尝试从请求中获取令牌并验证
        auth_service = self.get_auth_service()
        if auth_service:
            try:
                token = self._get_token_from_request()
                if token:
                    user = auth_service.verify_token(token)
                    if user:
                        g.current_user = user
                        return user
            except Exception as e:
                logger.warning(f"获取当前用户失败: {str(e)}")
        
        return None
    
    def _get_token_from_request(self):
        """从请求中获取认证令牌"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        
        # 尝试从查询参数获取令牌
        token = request.args.get('token')
        if token:
            return token
        
        # 尝试从Cookie获取令牌
        token = request.cookies.get('token')
        if token:
            return token
        
        return None
    
    def check_permission(self, user, permission_name, resource=None):
        """
        检查用户是否具有指定权限
        
        Args:
            user: 用户对象
            permission_name: 权限名称
            resource: 资源对象，用于基于资源的权限检查
            
        Returns:
            bool: 是否具有权限
        """
        if user is None:
            return False
        
        # 缓存键
        cache_key = f"{user.id}:{permission_name}:{id(resource) if resource else 'none'}"
        
        # 查询缓存
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        # 管理员拥有所有权限
        if hasattr(user, 'is_admin') and user.is_admin:
            self._permission_cache[cache_key] = True
            return True
        
        if hasattr(user, 'has_role') and user.has_role('admin'):
            self._permission_cache[cache_key] = True
            return True
        
        # 基于资源的权限检查
        if resource is not None and hasattr(user, 'can_access'):
            has_permission = user.can_access(resource, permission_name)
            self._permission_cache[cache_key] = has_permission
            return has_permission
            
        # 基于角色的权限检查
        if hasattr(user, 'has_permission'):
            has_permission = user.has_permission(permission_name)
            self._permission_cache[cache_key] = has_permission
            return has_permission
        
        # 默认无权限
        self._permission_cache[cache_key] = False
        return False
    
    def require_permission(self, permission_name, resource=None):
        """
        要求当前用户必须具有指定权限，否则抛出异常
        
        Args:
            permission_name: 权限名称
            resource: 资源对象，用于基于资源的权限检查
            
        Raises:
            AuthenticationError: 如果用户未认证
            AuthorizationError: 如果用户没有所需权限
            
        Returns:
            bool: 如果用户具有权限，返回True
        """
        user = self.get_current_user()
        if not user:
            raise AuthenticationError("需要登录")
        
        if not self.check_permission(user, permission_name, resource):
            logger.warning(f"用户 {user.id} 无权限: {permission_name}")
            raise AuthorizationError(f"没有 {permission_name} 权限")
        
        return True
    
    def permission_required(self, permission_name, resource_loader=None):
        """
        要求用户具有特定权限的装饰器
        支持 Web 和 API 认证
        
        Args:
            permission_name: 所需的权限名称
            resource_loader: 资源加载函数，用于基于资源的权限检查
                函数签名: resource_loader(*args, **kwargs) -> resource_object
        """
        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    user = self.get_current_user()
                    
                    # 检查用户是否已认证
                    if not user:
                        if request.is_json:
                            return jsonify({
                                "status": "error",
                                "message": "需要登录",
                                "code": "login_required"
                            }), 401
                        return redirect(url_for('auth.login', next=request.url))
                    
                    # 如果提供了资源加载器，则加载资源
                    resource = None
                    if resource_loader:
                        try:
                            resource = resource_loader(*args, **kwargs)
                        except Exception as e:
                            logger.error(f"加载资源失败: {str(e)}")
                    
                    # 检查权限
                    if not self.check_permission(user, permission_name, resource):
                        if request.is_json:
                            logger.warning(f"用户 {user.id} 无权限: {permission_name}")
                            return jsonify({
                                "status": "error",
                                "message": f"需要 {permission_name} 权限",
                                "code": "permission_denied"
                            }), 403
                        return redirect(url_for('main.index'))
                    
                    # 权限检查通过，调用原函数
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    logger.exception(f"权限检查过程中发生错误: {str(e)}")
                    if request.is_json:
                        return jsonify({
                            "status": "error",
                            "message": "权限检查失败",
                            "code": "permission_check_error"
                        }), 500
                    return redirect(url_for('main.index'))
            
            # 标记该函数需要权限检查
            decorated_function._requires_permission = permission_name
            return decorated_function
        
        return decorator
    
    def role_required(self, role_name):
        """
        要求用户具有特定角色的装饰器
        
        Args:
            role_name: 所需的角色名称
        """
        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                user = self.get_current_user()
                
                # 检查用户是否已认证
                if not user:
                    if request.is_json:
                        return jsonify({
                            "status": "error",
                            "message": "需要登录",
                            "code": "login_required"
                        }), 401
                    return redirect(url_for('auth.login', next=request.url))
                
                # 检查用户角色
                if not hasattr(user, 'has_role') or not user.has_role(role_name):
                    if request.is_json:
                        logger.warning(f"用户 {user.id} 无角色: {role_name}")
                        return jsonify({
                            "status": "error",
                            "message": f"需要 {role_name} 角色",
                            "code": "role_denied"
                        }), 403
                    return redirect(url_for('main.index'))
                
                # 角色检查通过，调用原函数
                return f(*args, **kwargs)
            
            # 标记该函数需要角色检查
            decorated_function._requires_role = role_name
            return decorated_function
        
        return decorator
    
    def admin_required(self, f=None):
        """
        要求用户具有管理员权限的装饰器
        可以直接使用 @admin_required 或 @admin_required()
        """
        if f is None:
            return self.role_required('admin')
        
        return self.role_required('admin')(f)
    
    def clear_permission_cache(self, user_id=None):
        """
        清除权限缓存
        
        Args:
            user_id: 如果提供，则只清除该用户的缓存
        """
        if user_id:
            prefix = f"{user_id}:"
            self._permission_cache = {k: v for k, v in self._permission_cache.items() if not k.startswith(prefix)}
        else:
            self._permission_cache.clear()

# 创建权限管理器单例
permission_manager = PermissionManager()

# 导出便捷函数和装饰器
def init_permission_manager(app, auth_service=None):
    """初始化权限管理器"""
    permission_manager.init_app(app, auth_service)

def check_permission(user, permission_name, resource=None):
    """检查用户是否具有指定权限"""
    return permission_manager.check_permission(user, permission_name, resource)

def require_permission(permission_name, resource=None):
    """要求当前用户必须具有指定权限，否则抛出异常"""
    return permission_manager.require_permission(permission_name, resource)

def permission_required(permission_name, resource_loader=None):
    """要求用户具有特定权限的装饰器"""
    return permission_manager.permission_required(permission_name, resource_loader)

def role_required(role_name):
    """要求用户具有特定角色的装饰器"""
    return permission_manager.role_required(role_name)

def admin_required(f=None):
    """要求用户具有管理员权限的装饰器"""
    return permission_manager.admin_required(f) 