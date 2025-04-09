#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API V1模块
注册v1版本的所有API蓝图
"""

from flask import Blueprint
from app.api.v1.auth import auth_bp
from app.api.v1.user import user_bp
from app.api.v1.correction import correction_bp
from app.api.v1.membership import membership_bp, payment_bp
from app.api.v1.analytics import analytics_bp
from app.api.v1.notification import notification_bp
from app.api.v1.essays import essays_bp
from app.api.v1.admin import admin_api_bp

# 创建API v1蓝图
api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# 注册所有API蓝图
api_v1_bp.register_blueprint(auth_bp)
api_v1_bp.register_blueprint(user_bp)
api_v1_bp.register_blueprint(correction_bp)
api_v1_bp.register_blueprint(membership_bp)
api_v1_bp.register_blueprint(payment_bp)
api_v1_bp.register_blueprint(analytics_bp)
api_v1_bp.register_blueprint(notification_bp)
api_v1_bp.register_blueprint(essays_bp)
api_v1_bp.register_blueprint(admin_api_bp)

__all__ = ['api_v1_bp'] 