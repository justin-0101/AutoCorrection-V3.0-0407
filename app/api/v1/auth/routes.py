#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证API路由
处理用户登录、注册、验证码等API
"""

import logging
from flask import Blueprint, request, jsonify, current_app, g

from app.core.auth import AuthService, ValidationService, login_required
from app.utils.exceptions import ValidationError, AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        # 获取并验证请求数据
        data = request.get_json()
        if not data:
            raise ValidationError("无效的请求数据")
        
        # 验证注册数据
        ValidationService.validate_registration_data(data)
        
        # 注册用户
        user_info = AuthService.register(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            name=data.get('name')
        )
        
        return jsonify({
            "status": "success",
            "message": "注册成功",
            "data": user_info
        })
    
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "errors": getattr(e, 'errors', None)
        }), 400
    
    except Exception as e:
        logger.exception(f"注册异常: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "注册失败，请稍后再试"
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        # 获取并验证请求数据
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
            
        if not data:
            raise ValidationError("无效的请求数据")
        
        # 验证登录数据
        ValidationService.validate_login_data(data)
        
        # 验证用户凭据
        user = AuthService.authenticate(
            username_or_email=data.get('username'),  # 改为使用username_or_email
            password=data.get('password')
        )
        
        if not user:
            raise AuthenticationError("用户名或密码错误")
        
        # 设置用户会话
        from flask_login import login_user
        login_user(user)
        
        return jsonify({
            "status": "success",
            "message": "登录成功",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "is_admin": user.is_admin
            }
        })
    
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "errors": getattr(e, 'errors', None)
        }), 400
    
    except AuthenticationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 401
    
    except Exception as e:
        logger.exception(f"登录异常: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "登录失败，请稍后再试"
        }), 500

@auth_bp.route('/verify', methods=['GET'])
@login_required
def verify_token():
    """验证令牌并返回当前用户信息"""
    try:
        # 获取当前用户（已由login_required装饰器验证）
        user_info = AuthService.get_current_user()
        
        return jsonify({
            "status": "success",
            "message": "令牌有效",
            "data": user_info
        })
    
    except Exception as e:
        logger.exception(f"验证令牌异常: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "验证失败，请稍后再试"
        }), 500

@auth_bp.route('/password/change', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    try:
        # 获取并验证请求数据
        data = request.get_json()
        if not data:
            raise ValidationError("无效的请求数据")
        
        # 验证修改密码数据
        ValidationService.validate_change_password_data(data)
        
        # 获取当前用户ID
        user_id = g.current_user.id
        
        # 修改密码
        AuthService.change_password(
            user_id=user_id,
            old_password=data.get('old_password'),
            new_password=data.get('new_password')
        )
        
        return jsonify({
            "status": "success",
            "message": "密码修改成功"
        })
    
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "errors": getattr(e, 'errors', None)
        }), 400
    
    except Exception as e:
        logger.exception(f"修改密码异常: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "修改密码失败，请稍后再试"
        }), 500

@auth_bp.route('/password/reset/request', methods=['POST'])
def request_reset_password():
    """请求重置密码"""
    try:
        # 获取并验证请求数据
        data = request.get_json()
        if not data:
            raise ValidationError("无效的请求数据")
        
        email = data.get('email')
        if not email:
            raise ValidationError("邮箱不能为空")
        
        # 验证邮箱
        ValidationService.validate_email(email)
        
        # 发送验证码
        code = AuthService.send_verification_code(email, purpose='password_reset')
        
        return jsonify({
            "status": "success",
            "message": "验证码已发送，请检查邮箱"
        })
    
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    
    except Exception as e:
        logger.exception(f"请求重置密码异常: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "发送验证码失败，请稍后再试"
        }), 500

@auth_bp.route('/password/reset/confirm', methods=['POST'])
def confirm_reset_password():
    """确认重置密码"""
    try:
        # 获取并验证请求数据
        data = request.get_json()
        if not data:
            raise ValidationError("无效的请求数据")
        
        # 验证重置密码数据
        ValidationService.validate_reset_password_data(data)
        
        # 重置密码
        AuthService.reset_password(
            email=data.get('email'),
            verification_code=data.get('code'),
            new_password=data.get('new_password')
        )
        
        return jsonify({
            "status": "success",
            "message": "密码重置成功"
        })
    
    except ValidationError as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "errors": getattr(e, 'errors', None)
        }), 400
    
    except Exception as e:
        logger.exception(f"确认重置密码异常: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "重置密码失败，请稍后再试"
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    try:
        # 获取令牌
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token.replace('Bearer ', '')
        
        # 实际应用中应该将token加入黑名单
        # 这里简化处理，不做具体实现
        
        return jsonify({
            "status": "success",
            "message": "登出成功"
        })
    
    except Exception as e:
        logger.exception(f"登出异常: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "登出失败，请稍后再试"
        }), 500 