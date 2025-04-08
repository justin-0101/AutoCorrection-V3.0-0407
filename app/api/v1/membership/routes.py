#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员订阅API路由模块
处理会员计划查询、订阅管理和支付相关的API接口
"""

import logging
from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.core.membership.membership_service import MembershipService
from app.core.subscription.subscription_service import SubscriptionService
from app.core.payment.payment_service import PaymentService
from app.api.decorators import validate_json, handle_exceptions
from app.core.auth.auth_decorators import login_required

logger = logging.getLogger(__name__)

# 创建Blueprint
membership_bp = Blueprint("membership_api", __name__, url_prefix="/membership")
payment_bp = Blueprint("payment_api", __name__, url_prefix="/payment")

# 初始化服务
membership_service = MembershipService()
subscription_service = SubscriptionService()
payment_service = PaymentService()


# 会员计划相关API
@membership_bp.route("/plans", methods=["GET"])
@handle_exceptions
def get_membership_plans():
    """
    获取所有会员计划列表
    
    Returns:
        JSON: 会员计划列表
    """
    plans = subscription_service.get_plans()
    
    return jsonify({
        "status": "success",
        "plans": plans
    }), 200


@membership_bp.route("/plans/<plan_id>", methods=["GET"])
@handle_exceptions
def get_plan_details(plan_id):
    """
    获取指定会员计划的详情
    
    Args:
        plan_id: 计划ID
        
    Returns:
        JSON: 计划详情
    """
    result = subscription_service.get_plan_details(plan_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 404


@membership_bp.route("/user", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_user_membership():
    """
    获取当前用户的会员信息
    
    Returns:
        JSON: 用户会员信息
    """
    user_id = get_jwt_identity()
    
    result = membership_service.get_user_membership(user_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


# 订阅相关API
@membership_bp.route("/subscriptions", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_user_subscriptions():
    """
    获取当前用户的订阅列表
    
    Returns:
        JSON: 用户订阅列表
    """
    user_id = get_jwt_identity()
    
    result = subscription_service.get_user_subscriptions(user_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@membership_bp.route("/subscriptions/<int:subscription_id>", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_subscription_details(subscription_id):
    """
    获取指定订阅的详情
    
    Args:
        subscription_id: 订阅ID
        
    Returns:
        JSON: 订阅详情
    """
    user_id = get_jwt_identity()
    
    result = subscription_service.get_subscription_details(user_id, subscription_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@membership_bp.route("/subscribe", methods=["POST"])
@jwt_required()
@validate_json({"plan_id": str, "duration": str})
@handle_exceptions
def create_subscription():
    """
    创建新的会员订阅
    
    Request JSON:
        {
            "plan_id": "basic",     # 计划ID
            "duration": "monthly"    # 订阅时长 (monthly/yearly)
        }
        
    Returns:
        JSON: 创建结果
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    plan_id = data.get("plan_id")
    duration = data.get("duration")
    
    result = subscription_service.create_subscription(user_id, plan_id, duration)
    
    if result.get("status") == "success":
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@membership_bp.route("/subscriptions/<int:subscription_id>/cancel", methods=["POST"])
@jwt_required()
@handle_exceptions
def cancel_subscription(subscription_id):
    """
    取消指定的订阅
    
    Args:
        subscription_id: 订阅ID
        
    Returns:
        JSON: 取消结果
    """
    user_id = get_jwt_identity()
    
    result = subscription_service.cancel_subscription(user_id, subscription_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@membership_bp.route("/subscriptions/<int:subscription_id>/auto-renew", methods=["POST"])
@jwt_required()
@handle_exceptions
def toggle_auto_renew(subscription_id):
    """
    切换订阅的自动续费状态
    
    Args:
        subscription_id: 订阅ID
        
    Returns:
        JSON: 切换结果
    """
    user_id = get_jwt_identity()
    
    result = subscription_service.toggle_auto_renew(user_id, subscription_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


# 支付相关API
@payment_bp.route("/methods", methods=["GET"])
@handle_exceptions
def get_payment_methods():
    """
    获取支持的支付方式
    
    Returns:
        JSON: 支付方式列表
    """
    result = payment_service.get_payment_methods()
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@payment_bp.route("/subscriptions/<int:subscription_id>/pay", methods=["POST"])
@jwt_required()
@validate_json({"payment_method": str})
@handle_exceptions
def pay_subscription(subscription_id):
    """
    为指定订阅创建支付
    
    Args:
        subscription_id: 订阅ID
        
    Request JSON:
        {
            "payment_method": "alipay"  # 支付方式
        }
        
    Returns:
        JSON: 支付创建结果
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    payment_method = data.get("payment_method")
    
    # 检查订阅是否属于当前用户
    subscription_details = subscription_service.get_subscription_details(user_id, subscription_id)
    if subscription_details.get("status") != "success":
        return jsonify(subscription_details), 400
    
    # 创建支付
    result = subscription_service.pay_subscription(subscription_id, payment_method)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@payment_bp.route("/query/<int:payment_id>", methods=["GET"])
@jwt_required()
@handle_exceptions
def query_payment(payment_id):
    """
    查询支付状态
    
    Args:
        payment_id: 支付ID
        
    Returns:
        JSON: 支付状态
    """
    result = payment_service.query_payment_status(payment_id)
    
    if result.get("status") in ["success", "pending"]:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@payment_bp.route("/callback/<payment_method>", methods=["POST"])
@handle_exceptions
def payment_callback(payment_method):
    """
    支付回调接口
    
    Args:
        payment_method: 支付方式
        
    Returns:
        JSON: 回调处理结果
    """
    # 获取回调数据
    callback_data = request.json or request.form.to_dict() or {}
    
    # 处理支付回调
    result = payment_service.process_payment_callback(payment_method, callback_data)
    
    if result.get("status") == "success":
        # 激活订阅
        subscription_id = result.get("subscription_id")
        if subscription_id:
            subscription_service.activate_subscription(subscription_id)
        
        return jsonify({"success": True}), 200
    else:
        logger.error(f"支付回调处理失败: {result.get('message')}")
        return jsonify({"success": False, "message": result.get("message")}), 400


@payment_bp.route("/<int:payment_id>/cancel", methods=["POST"])
@jwt_required()
@handle_exceptions
def cancel_payment(payment_id):
    """
    取消支付
    
    Args:
        payment_id: 支付ID
        
    Returns:
        JSON: 取消结果
    """
    result = payment_service.cancel_payment(payment_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400