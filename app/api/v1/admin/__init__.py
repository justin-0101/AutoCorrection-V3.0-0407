#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
管理员 API 包
"""

from flask import Blueprint

from app.api.v1.admin.routes import admin_api_bp

__all__ = ['admin_api_bp'] 