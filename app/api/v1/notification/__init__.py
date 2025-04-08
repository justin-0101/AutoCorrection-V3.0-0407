#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知API模块
导出通知相关的API蓝图
"""

from app.api.v1.notification.routes import notification_bp

__all__ = ['notification_bp'] 