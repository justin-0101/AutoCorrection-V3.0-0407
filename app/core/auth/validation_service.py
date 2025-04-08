#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证服务
提供表单和数据验证功能
"""

import re
import logging
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)

# 正则表达式
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,20}$')  # 3-20个字符，只能是字母、数字、下划线
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')  # 标准email格式
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{8,}$')  # 最少8个字符，至少包含一个字母和一个数字

class ValidationService:
    """验证服务类"""
    
    @staticmethod
    def validate_username(username):
        """验证用户名"""
        if not username:
            raise ValidationError("用户名不能为空")
        
        if not isinstance(username, str):
            raise ValidationError("用户名必须是字符串")
        
        if not USERNAME_REGEX.match(username):
            raise ValidationError("用户名必须是3-20个字符，只能包含字母、数字和下划线")
        
        return True
    
    @staticmethod
    def validate_email(email):
        """验证邮箱"""
        if not email:
            raise ValidationError("邮箱不能为空")
        
        if not isinstance(email, str):
            raise ValidationError("邮箱必须是字符串")
        
        if not EMAIL_REGEX.match(email):
            raise ValidationError("邮箱格式不正确")
        
        return True
    
    @staticmethod
    def validate_password(password, is_registration=False):
        """
        验证密码
        
        Args:
            password: 密码
            is_registration: 是否是注册场景，注册时需要验证密码强度
        """
        if not password:
            raise ValidationError("密码不能为空")
        
        if not isinstance(password, str):
            raise ValidationError("密码必须是字符串")
        
        if is_registration and not PASSWORD_REGEX.match(password):
            raise ValidationError("密码必须至少包含8个字符，且至少包含一个字母和一个数字")
        
        return True
    
    @staticmethod
    def validate_registration_data(data):
        """验证注册数据"""
        errors = {}
        
        # 验证用户名
        try:
            ValidationService.validate_username(data.get('username'))
        except ValidationError as e:
            errors['username'] = str(e)
        
        # 验证邮箱
        try:
            ValidationService.validate_email(data.get('email'))
        except ValidationError as e:
            errors['email'] = str(e)
        
        # 验证密码
        try:
            ValidationService.validate_password(data.get('password'), is_registration=True)
        except ValidationError as e:
            errors['password'] = str(e)
        
        # 验证确认密码
        if data.get('password') != data.get('confirm_password'):
            errors['confirm_password'] = "两次输入的密码不一致"
        
        if errors:
            raise ValidationError("注册数据验证失败", errors=errors)
        
        return True
    
    @staticmethod
    def validate_login_data(data):
        """验证登录数据"""
        errors = {}
        
        # 验证用户名或邮箱
        username = data.get('username')
        if not username:
            errors['username'] = "用户名或邮箱不能为空"
        
        # 验证密码
        if not data.get('password'):
            errors['password'] = "密码不能为空"
        
        if errors:
            raise ValidationError("登录数据验证失败", errors=errors)
        
        return True
    
    @staticmethod
    def validate_change_password_data(data):
        """验证修改密码数据"""
        errors = {}
        
        # 验证原密码
        if not data.get('old_password'):
            errors['old_password'] = "原密码不能为空"
        
        # 验证新密码
        try:
            ValidationService.validate_password(data.get('new_password'), is_registration=True)
        except ValidationError as e:
            errors['new_password'] = str(e)
        
        # 验证确认密码
        if data.get('new_password') != data.get('confirm_password'):
            errors['confirm_password'] = "两次输入的密码不一致"
        
        if errors:
            raise ValidationError("修改密码数据验证失败", errors=errors)
        
        return True
    
    @staticmethod
    def validate_reset_password_data(data):
        """验证重置密码数据"""
        errors = {}
        
        # 验证邮箱
        try:
            ValidationService.validate_email(data.get('email'))
        except ValidationError as e:
            errors['email'] = str(e)
        
        # 验证验证码
        if not data.get('code'):
            errors['code'] = "验证码不能为空"
        elif len(str(data.get('code'))) != 6:
            errors['code'] = "验证码必须是6位数字"
        
        # 验证新密码
        try:
            ValidationService.validate_password(data.get('new_password'), is_registration=True)
        except ValidationError as e:
            errors['new_password'] = str(e)
        
        # 验证确认密码
        if data.get('new_password') != data.get('confirm_password'):
            errors['confirm_password'] = "两次输入的密码不一致"
        
        if errors:
            raise ValidationError("重置密码数据验证失败", errors=errors)
        
        return True 