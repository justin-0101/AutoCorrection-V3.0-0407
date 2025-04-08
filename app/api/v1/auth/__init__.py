#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证API模块
包含用户登录、注册、密码管理等API
"""

from app.api.v1.auth.routes import auth_bp

__all__ = ['auth_bp'] 