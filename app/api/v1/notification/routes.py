#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知API路由模块
处理用户通知相关的API接口
"""

import logging
from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.core.notification.notification_service import NotificationService
from app.api.decorators import handle_exceptions

logger = logging.getLogger(__name__)

# 创建Blueprint
notification_bp = Blueprint("notification_api", __name__, url_prefix="/notifications")

# 初始化服务
notification_service = NotificationService()


@notification_bp.route("", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_notifications():
    """
    获取当前用户的通知
    
    Query Parameters:
        page: 页码，默认1
        per_page: 每页条数，默认20
        unread_only: 是否只获取未读通知，默认false
        
    Returns:
        JSON: 通知列表
    """
    user_id = get_jwt_identity()
    
    # 获取查询参数
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    
    # 获取通知列表
    result = notification_service.get_user_notifications(
        user_id=user_id,
        page=page,
        per_page=per_page,
        unread_only=unread_only
    )
    
    return jsonify(result), 200


@notification_bp.route("/unread-count", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_unread_count():
    """
    获取当前用户未读通知数量
    
    Returns:
        JSON: 未读通知数量
    """
    user_id = get_jwt_identity()
    
    # 只获取未读通知的数量
    result = notification_service.get_user_notifications(
        user_id=user_id,
        page=1,
        per_page=1,
        unread_only=True
    )
    
    return jsonify({
        "status": "success",
        "unread_count": result.get("total", 0)
    }), 200


@notification_bp.route("/<int:notification_id>/read", methods=["POST"])
@jwt_required()
@handle_exceptions
def mark_as_read(notification_id):
    """
    标记特定通知为已读
    
    Args:
        notification_id: 通知ID
        
    Returns:
        JSON: 操作结果
    """
    user_id = get_jwt_identity()
    
    result = notification_service.mark_notification_read(
        notification_id=notification_id,
        user_id=user_id
    )
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@notification_bp.route("/read-all", methods=["POST"])
@jwt_required()
@handle_exceptions
def mark_all_read():
    """
    标记所有通知为已读
    
    Returns:
        JSON: 操作结果
    """
    user_id = get_jwt_identity()
    
    result = notification_service.mark_all_notifications_read(user_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@notification_bp.route("/<int:notification_id>", methods=["DELETE"])
@jwt_required()
@handle_exceptions
def delete_notification(notification_id):
    """
    删除特定通知
    
    Args:
        notification_id: 通知ID
        
    Returns:
        JSON: 操作结果
    """
    user_id = get_jwt_identity()
    
    result = notification_service.delete_notification(
        notification_id=notification_id,
        user_id=user_id
    )
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400 