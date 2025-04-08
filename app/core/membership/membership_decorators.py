#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员系统装饰器模块
提供会员权限检查和配额管理的装饰器
"""

import logging
from functools import wraps
from flask import request, jsonify, g, current_app

from app.core.membership.membership_service import MembershipService
from app.utils.exceptions import PermissionError, QuotaExceededError

# 获取logger
logger = logging.getLogger(__name__)

def membership_required():
    """
    会员权限检查装饰器
    检查用户是否有会员权限
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 检查用户是否已登录
                if not hasattr(g, 'current_user') or not g.current_user:
                    return jsonify({
                        "status": "error",
                        "code": "authentication_required",
                        "message": "请先登录"
                    }), 401
                
                # 获取会员服务
                membership_service = MembershipService()
                
                # 检查会员资格
                if not membership_service.check_membership(g.current_user.id):
                    logger.warning(f"用户无会员权限，用户ID: {g.current_user.id}")
                    return jsonify({
                        "status": "error",
                        "code": "membership_required",
                        "message": "此功能需要会员权限"
                    }), 403
                
                return f(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"会员权限检查异常: {str(e)}")
                return jsonify({
                    "status": "error",
                    "code": "internal_error",
                    "message": "会员权限检查失败"
                }), 500
                
        return decorated_function
    return decorator

def check_essay_quota():
    """
    作文配额检查装饰器
    检查用户是否有足够的作文批改配额
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 检查用户是否已登录
                if not hasattr(g, 'current_user') or not g.current_user:
                    return jsonify({
                        "status": "error",
                        "code": "authentication_required",
                        "message": "请先登录"
                    }), 401
                
                # 获取会员服务
                membership_service = MembershipService()
                
                # 检查配额
                quota_info = membership_service.check_essay_quota(g.current_user.id)
                
                if quota_info.get("status") != "success":
                    return jsonify({
                        "status": "error",
                        "code": "quota_check_failed",
                        "message": quota_info.get("message", "配额检查失败")
                    }), 500
                
                quota_data = quota_info.get("data", {})
                
                # 检查是否有足够配额
                if not quota_data.get("has_quota", False) and not quota_data.get("is_admin", False):
                    logger.warning(f"用户作文配额不足，用户ID: {g.current_user.id}")
                    return jsonify({
                        "status": "error",
                        "code": "quota_exceeded",
                        "message": "您的作文批改次数已用完",
                        "data": {
                            "monthly_limit": quota_data.get("monthly_limit", 0),
                            "monthly_used": quota_data.get("monthly_used", 0),
                            "monthly_remaining": quota_data.get("monthly_remaining", 0)
                        }
                    }), 403
                
                # 请求处理前记录配额信息
                g.quota_info = quota_data
                
                # 处理请求
                response = f(*args, **kwargs)
                
                # 请求成功后，增加使用量（仅对POST请求）
                if request.method == 'POST' and isinstance(response, tuple) and response[1] == 200:
                    increment_result = membership_service.increment_essay_usage(g.current_user.id)
                    logger.info(f"作文使用量已增加，用户ID: {g.current_user.id}, 结果: {increment_result}")
                
                return response
            
            except Exception as e:
                logger.error(f"作文配额检查异常: {str(e)}")
                return jsonify({
                    "status": "error",
                    "code": "internal_error",
                    "message": "作文配额检查失败"
                }), 500
                
        return decorated_function
    return decorator

def premium_feature():
    """
    高级功能装饰器
    用于标记和限制只有高级会员才能使用的功能
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 检查用户是否已登录
                if not hasattr(g, 'current_user') or not g.current_user:
                    return jsonify({
                        "status": "error",
                        "code": "authentication_required",
                        "message": "请先登录"
                    }), 401
                
                # 获取会员服务
                membership_service = MembershipService()
                
                # 获取用户会员信息
                membership_info = membership_service.get_user_membership(g.current_user.id)
                
                if membership_info.get("status") != "success":
                    return jsonify({
                        "status": "error",
                        "code": "membership_check_failed",
                        "message": membership_info.get("message", "会员检查失败")
                    }), 500
                
                membership_data = membership_info.get("data", {})
                
                # 检查是否是高级会员
                if not membership_data.get("is_premium", False) and g.current_user.role != 'admin':
                    logger.warning(f"用户尝试访问高级功能，但不是高级会员，用户ID: {g.current_user.id}")
                    return jsonify({
                        "status": "error",
                        "code": "premium_required",
                        "message": "此功能需要高级会员权限",
                        "data": {
                            "membership_status": membership_data.get("membership_status", "免费用户"),
                            "membership_expires": membership_data.get("membership_expires")
                        }
                    }), 403
                
                return f(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"高级功能检查异常: {str(e)}")
                return jsonify({
                    "status": "error",
                    "code": "internal_error",
                    "message": "高级功能检查失败"
                }), 500
                
        return decorated_function
    return decorator 