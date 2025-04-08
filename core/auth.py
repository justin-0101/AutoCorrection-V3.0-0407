import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, jsonify
from core.user_model import User
from utils.exceptions import AuthenticationError

logger = logging.getLogger('autocorrection.auth')

def login_required(f):
    """验证用户令牌的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求获取令牌
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            logger.warning("缺少认证令牌")
            return jsonify({"success": False, "message": "需要登录"}), 401
        
        token = token.replace('Bearer ', '')
        user = User.find_by_token(token)
        
        if not user:
            logger.warning(f"令牌无效: {token[:10]}...")
            return jsonify({"success": False, "message": "令牌无效或已过期"}), 401
        
        # 将用户设置为全局上下文
        g.user = user
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """验证管理员权限的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 先验证用户登录
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            logger.warning("缺少认证令牌")
            return jsonify({"success": False, "message": "需要登录"}), 401
        
        token = token.replace('Bearer ', '')
        user = User.find_by_token(token)
        
        if not user:
            logger.warning(f"令牌无效: {token[:10]}...")
            return jsonify({"success": False, "message": "令牌无效或已过期"}), 401
            
        # 检查管理员权限
        if user.user_type != 'admin':
            logger.warning(f"非管理员访问: 用户 {user.id}")
            return jsonify({"success": False, "message": "需要管理员权限"}), 403
        
        # 将用户设置为全局上下文
        g.user = user
        return f(*args, **kwargs)
    
    return decorated_function

def authenticate_user(email, password):
    """验证用户登录"""
    user = User.authenticate(email, password)
    if not user:
        logger.warning(f"登录失败: {email}")
        raise AuthenticationError("邮箱或密码错误")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "user_type": user.user_type,
        "token": user.token
    }

def get_current_user():
    """获取当前登录用户（从请求上下文）"""
    user = getattr(g, 'user', None)
    if not user:
        return None
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "user_type": user.user_type
    }

def register_user(username, email, password):
    """注册新用户"""
    user = User.register(username, email, password)
    logger.info(f"用户注册成功: {email}")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "user_type": user.user_type,
        "token": user.token
    } 