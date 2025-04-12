#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
监控模块初始化
"""

from app.api.v1.monitoring.routes import monitoring_bp

def init_app(app):
    """注册监控模块"""
    from app.api.v1.monitoring.routes import init_app as init_routes
    init_routes(app) 