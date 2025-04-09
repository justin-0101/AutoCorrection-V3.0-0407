#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自定义错误类
"""

class BaseError(Exception):
    """基础错误类"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class ValidationError(BaseError):
    """数据验证错误"""
    pass

class ResourceNotFoundError(BaseError):
    """资源未找到错误"""
    pass

class ProcessingError(BaseError):
    """处理过程错误"""
    pass

class AuthenticationError(BaseError):
    """认证错误"""
    pass

class AuthorizationError(BaseError):
    """授权错误"""
    pass

class ConfigurationError(BaseError):
    """配置错误"""
    pass

class ServiceError(BaseError):
    """服务错误"""
    pass 