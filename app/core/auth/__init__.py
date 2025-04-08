#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证模块
提供用户认证、授权和验证功能
"""

from app.core.auth.auth_service import AuthService
from app.core.auth.auth_decorators import (
    login_required, 
    admin_required, 
    permission_required, 
    role_required
)
from app.core.auth.validation_service import ValidationService

# 导出所有功能
__all__ = [
    'AuthService',
    'ValidationService',
    'login_required',
    'admin_required',
    'permission_required',
    'role_required',
] 