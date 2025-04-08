#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员数据分析API接口
提供会员使用统计、转化率、续费率等数据查询接口
"""

import logging
from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.core.analytics.membership_analytics import MembershipAnalytics
from app.core.analytics.usage_analytics import UsageAnalytics
from app.core.auth.auth_decorators import admin_required
from app.api.decorators import handle_exceptions

logger = logging.getLogger(__name__)

# 创建Blueprint
analytics_bp = Blueprint("analytics_api", __name__, url_prefix="/analytics")


# 用户级别API
@analytics_bp.route("/user/usage", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_user_usage_stats():
    """
    获取当前用户的会员使用统计
    
    Returns:
        JSON: 会员使用统计数据
    """
    user_id = get_jwt_identity()
    result = MembershipAnalytics.get_membership_usage_stats(user_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/user/history", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_user_usage_history():
    """
    获取当前用户的使用历史记录
    
    Query Parameters:
        event_type (str, optional): 筛选特定事件类型
        start_date (str, optional): 开始日期，格式为YYYY-MM-DD
        end_date (str, optional): 结束日期，格式为YYYY-MM-DD
        limit (int, optional): 返回记录数量限制，默认100
    
    Returns:
        JSON: 使用历史记录
    """
    import datetime
    
    user_id = get_jwt_identity()
    event_type = request.args.get("event_type")
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    limit = int(request.args.get("limit", 100))
    
    # 处理日期参数
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "开始日期格式无效，应为YYYY-MM-DD"
            }), 400
    
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
            # 设置为当天结束时间
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "结束日期格式无效，应为YYYY-MM-DD"
            }), 400
    
    result = UsageAnalytics.get_user_usage_history(
        user_id, event_type, start_date, end_date, limit
    )
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/user/predictions", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_usage_predictions():
    """
    获取当前用户的会员使用预测
    
    Returns:
        JSON: 会员使用预测数据
    """
    user_id = get_jwt_identity()
    result = MembershipAnalytics.get_membership_usage_predictions(user_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/user/engagement", methods=["GET"])
@jwt_required()
@handle_exceptions
def get_user_engagement():
    """
    获取当前用户的参与度指标
    
    Returns:
        JSON: 用户参与度指标数据
    """
    user_id = get_jwt_identity()
    result = UsageAnalytics.get_user_engagement_metrics(user_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


# 管理员级别API
@analytics_bp.route("/admin/conversions", methods=["GET"])
@jwt_required()
@admin_required
@handle_exceptions
def get_conversion_stats():
    """
    获取会员转化率统计（管理员接口）
    
    Query Parameters:
        period_days (int, optional): 统计周期天数，默认30
    
    Returns:
        JSON: 会员转化统计数据
    """
    period_days = int(request.args.get("period_days", 30))
    result = MembershipAnalytics.get_membership_conversion_stats(period_days)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/admin/renewals", methods=["GET"])
@jwt_required()
@admin_required
@handle_exceptions
def get_renewal_stats():
    """
    获取会员续订率统计（管理员接口）
    
    Query Parameters:
        period_days (int, optional): 统计周期天数，默认90
    
    Returns:
        JSON: 会员续订统计数据
    """
    period_days = int(request.args.get("period_days", 90))
    result = MembershipAnalytics.get_membership_renewal_stats(period_days)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/admin/usage-trends", methods=["GET"])
@jwt_required()
@admin_required
@handle_exceptions
def get_usage_trends():
    """
    获取会员使用趋势统计（管理员接口）
    
    Query Parameters:
        period_days (int, optional): 统计周期天数，默认90
    
    Returns:
        JSON: 会员使用趋势统计数据
    """
    period_days = int(request.args.get("period_days", 90))
    result = UsageAnalytics.get_membership_usage_trends(period_days)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/admin/feature-usage", methods=["GET"])
@jwt_required()
@admin_required
@handle_exceptions
def get_feature_usage():
    """
    获取特定功能的使用统计（管理员接口）
    
    Query Parameters:
        feature (str): 功能名称
        period_days (int, optional): 统计周期天数，默认30
    
    Returns:
        JSON: 功能使用统计数据
    """
    feature = request.args.get("feature")
    if not feature:
        return jsonify({
            "status": "error",
            "message": "功能名称参数缺失"
        }), 400
    
    period_days = int(request.args.get("period_days", 30))
    result = UsageAnalytics.get_feature_usage_stats(feature, period_days)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/admin/quota-alerts", methods=["GET"])
@jwt_required()
@admin_required
@handle_exceptions
def get_quota_alerts():
    """
    获取即将达到使用配额的用户列表（管理员接口）
    
    Returns:
        JSON: 需要发送警报的用户列表
    """
    result = UsageAnalytics.get_usage_quota_alerts()
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@analytics_bp.route("/admin/user/<int:user_id>/usage", methods=["GET"])
@jwt_required()
@admin_required
@handle_exceptions
def get_specific_user_usage(user_id):
    """
    获取指定用户的会员使用统计（管理员接口）
    
    Args:
        user_id: 用户ID
    
    Returns:
        JSON: 会员使用统计数据
    """
    result = MembershipAnalytics.get_membership_usage_stats(user_id)
    
    if result.get("status") == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 400 