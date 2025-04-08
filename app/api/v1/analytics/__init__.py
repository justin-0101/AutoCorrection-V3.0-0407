#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员数据分析API模块
提供会员使用统计、转化率、续费率等数据查询接口
"""

from app.api.v1.analytics.routes import analytics_bp

__all__ = [
    'analytics_bp'
] 