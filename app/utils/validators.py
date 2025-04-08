#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据验证工具模块
"""

import re
from typing import Dict, Any, List, Optional
from app.utils.exceptions import ValidationError

def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """验证密码强度"""
    # 密码至少8位，包含大小写字母、数字和特殊字符
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    return bool(re.match(pattern, password))

def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_username(username: str) -> bool:
    """验证用户名格式"""
    # 用户名4-20位，只能包含字母、数字和下划线
    pattern = r'^[a-zA-Z0-9_]{4,20}$'
    return bool(re.match(pattern, username))

def validate_user_data(data: Dict[str, Any]) -> None:
    """验证用户数据"""
    errors: Dict[str, List[str]] = {}
    
    # 验证用户名
    if 'username' in data:
        if not isinstance(data['username'], str):
            errors.setdefault('username', []).append('用户名必须是字符串')
        elif not validate_username(data['username']):
            errors.setdefault('username', []).append('用户名格式不正确')
    
    # 验证邮箱
    if 'email' in data:
        if not isinstance(data['email'], str):
            errors.setdefault('email', []).append('邮箱必须是字符串')
        elif not validate_email(data['email']):
            errors.setdefault('email', []).append('邮箱格式不正确')
    
    # 验证手机号
    if 'phone' in data:
        if not isinstance(data['phone'], str):
            errors.setdefault('phone', []).append('手机号必须是字符串')
        elif not validate_phone(data['phone']):
            errors.setdefault('phone', []).append('手机号格式不正确')
    
    # 验证密码
    if 'password' in data:
        if not isinstance(data['password'], str):
            errors.setdefault('password', []).append('密码必须是字符串')
        elif not validate_password(data['password']):
            errors.setdefault('password', []).append('密码不符合安全要求')
    
    # 验证昵称
    if 'nickname' in data:
        if not isinstance(data['nickname'], str):
            errors.setdefault('nickname', []).append('昵称必须是字符串')
        elif len(data['nickname']) < 2 or len(data['nickname']) > 20:
            errors.setdefault('nickname', []).append('昵称长度必须在2-20个字符之间')
    
    if errors:
        raise ValidationError('数据验证失败', errors=errors)

def validate_essay_data(data: Dict[str, Any]) -> None:
    """验证文章数据"""
    errors: Dict[str, List[str]] = {}
    
    # 验证标题
    if 'title' not in data:
        errors['title'] = ['标题不能为空']
    elif not isinstance(data['title'], str):
        errors['title'] = ['标题必须是字符串']
    elif len(data['title']) < 1 or len(data['title']) > 100:
        errors['title'] = ['标题长度必须在1-100个字符之间']
    
    # 验证内容
    if 'content' not in data:
        errors['content'] = ['内容不能为空']
    elif not isinstance(data['content'], str):
        errors['content'] = ['内容必须是字符串']
    elif len(data['content']) < 10:
        errors['content'] = ['内容长度不能少于10个字符']
    
    # 验证标签
    if 'tags' in data:
        if not isinstance(data['tags'], list):
            errors['tags'] = ['标签必须是列表']
        else:
            for tag in data['tags']:
                if not isinstance(tag, str):
                    errors.setdefault('tags', []).append('标签必须是字符串')
                    break
                elif len(tag) < 1 or len(tag) > 20:
                    errors.setdefault('tags', []).append('标签长度必须在1-20个字符之间')
                    break
    
    if errors:
        raise ValidationError('数据验证失败', errors=errors)

def validate_comment_data(data: Dict[str, Any]) -> None:
    """验证评论数据"""
    errors: Dict[str, List[str]] = {}
    
    # 验证内容
    if 'content' not in data:
        errors['content'] = ['评论内容不能为空']
    elif not isinstance(data['content'], str):
        errors['content'] = ['评论内容必须是字符串']
    elif len(data['content']) < 1 or len(data['content']) > 1000:
        errors['content'] = ['评论内容长度必须在1-1000个字符之间']
    
    if errors:
        raise ValidationError('数据验证失败', errors=errors)

def validate_subscription_data(data: Dict[str, Any]) -> None:
    """验证订阅数据"""
    errors: Dict[str, List[str]] = {}
    
    # 验证订阅类型
    if 'plan_id' not in data:
        errors['plan_id'] = ['订阅计划ID不能为空']
    elif not isinstance(data['plan_id'], (int, str)):
        errors['plan_id'] = ['订阅计划ID格式不正确']
    
    # 验证支付方式
    if 'payment_method' not in data:
        errors['payment_method'] = ['支付方式不能为空']
    elif not isinstance(data['payment_method'], str):
        errors['payment_method'] = ['支付方式必须是字符串']
    
    # 验证自动续费
    if 'auto_renew' in data and not isinstance(data['auto_renew'], bool):
        errors['auto_renew'] = ['自动续费必须是布尔值']
    
    if errors:
        raise ValidationError('数据验证失败', errors=errors)

def validate_payment_data(data: Dict[str, Any]) -> None:
    """验证支付数据"""
    errors: Dict[str, List[str]] = {}
    
    # 验证金额
    if 'amount' not in data:
        errors['amount'] = ['支付金额不能为空']
    elif not isinstance(data['amount'], (int, float)):
        errors['amount'] = ['支付金额必须是数字']
    elif data['amount'] <= 0:
        errors['amount'] = ['支付金额必须大于0']
    
    # 验证支付方式
    if 'payment_method' not in data:
        errors['payment_method'] = ['支付方式不能为空']
    elif not isinstance(data['payment_method'], str):
        errors['payment_method'] = ['支付方式必须是字符串']
    
    # 验证订单描述
    if 'description' in data:
        if not isinstance(data['description'], str):
            errors['description'] = ['订单描述必须是字符串']
        elif len(data['description']) > 200:
            errors['description'] = ['订单描述不能超过200个字符']
    
    if errors:
        raise ValidationError('数据验证失败', errors=errors)

def validate_notification_settings(data: Dict[str, Any]) -> None:
    """验证通知设置"""
    errors: Dict[str, List[str]] = {}
    
    valid_channels = {'email', 'sms', 'push'}
    valid_types = {'system', 'subscription', 'comment', 'mention'}
    
    # 验证通知渠道
    if 'channels' in data:
        if not isinstance(data['channels'], dict):
            errors['channels'] = ['通知渠道设置必须是字典']
        else:
            for channel, enabled in data['channels'].items():
                if channel not in valid_channels:
                    errors.setdefault('channels', []).append(f'不支持的通知渠道: {channel}')
                elif not isinstance(enabled, bool):
                    errors.setdefault('channels', []).append(f'通知渠道状态必须是布尔值: {channel}')
    
    # 验证通知类型
    if 'types' in data:
        if not isinstance(data['types'], dict):
            errors['types'] = ['通知类型设置必须是字典']
        else:
            for type_, enabled in data['types'].items():
                if type_ not in valid_types:
                    errors.setdefault('types', []).append(f'不支持的通知类型: {type_}')
                elif not isinstance(enabled, bool):
                    errors.setdefault('types', []).append(f'通知类型状态必须是布尔值: {type_}')
    
    if errors:
        raise ValidationError('数据验证失败', errors=errors)

def validate_file_upload(file: Any, allowed_extensions: Optional[List[str]] = None,
                        max_size: Optional[int] = None) -> None:
    """验证文件上传"""
    errors: List[str] = []
    
    if not file:
        raise ValidationError('没有上传文件')
    
    if not file.filename:
        raise ValidationError('文件名不能为空')
    
    # 验证文件扩展名
    if allowed_extensions:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            raise ValidationError(f'不支持的文件类型，允许的类型：{", ".join(allowed_extensions)}')
    
    # 验证文件大小
    if max_size and file.content_length > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(f'文件大小超过限制，最大允许：{max_size_mb}MB') 