#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证相关异常类
"""

class AuthenticationError(Exception):
    """认证错误"""
    pass

class AuthorizationError(Exception):
    """授权错误"""
    pass

class ValidationError(Exception):
    """验证错误"""
    pass 