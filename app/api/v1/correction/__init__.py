#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改API模块
提供作文批改相关的RESTful API接口
"""

from app.api.v1.correction.routes import correction_bp

__all__ = ['correction_bp']
