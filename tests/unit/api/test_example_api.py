#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试示例API模块
验证统一权限检查和响应格式是否正常工作
"""

import json
import pytest
from flask import url_for
from flask_login import login_user

def test_hello_endpoint(client):
    """测试简单的问候端点"""
    response = client.get('/api/v1/example/hello')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['greeting'] == 'Hello, World!'
    assert 'message' in data

def test_hello_endpoint_with_name(client):
    """测试带参数的问候端点"""
    response = client.get('/api/v1/example/hello?name=测试用户')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['greeting'] == 'Hello, 测试用户!'

def test_custom_response_endpoint(client):
    """测试自定义响应消息和状态码端点"""
    response = client.get('/api/v1/example/custom')
    assert response.status_code == 201  # 确认使用了自定义状态码
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['message'] == '自定义成功消息'
    assert data['data']['custom'] is True

def test_protected_endpoint_without_login(client):
    """测试在未登录状态下访问受保护的端点"""
    response = client.get('/api/v1/example/protected')
    assert response.status_code == 302  # 未登录状态会先重定向到登录页
    # 确认有Location头，指向登录页
    assert 'Location' in response.headers
    assert '/login' in response.headers['Location']

def test_error_demo_validation_error(client):
    """测试验证错误处理"""
    response = client.get('/api/v1/example/error-demo?type=validation')
    assert response.status_code == 422
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'errors' in data
    assert 'field1' in data['errors']
    assert 'field2' in data['errors']

def test_error_demo_not_found(client):
    """测试资源不存在错误处理"""
    response = client.get('/api/v1/example/error-demo?type=not_found')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert '不存在' in data['message']

def test_error_demo_custom_error(client):
    """测试自定义错误处理"""
    response = client.get('/api/v1/example/error-demo?type=custom')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['message'] == '自定义错误消息'
    assert 'custom_error' in data['errors']
    assert data['code'] == 'CUSTOM_ERROR'

@pytest.mark.parametrize("error_type,expected_status", [
    (None, 500),  # 默认触发通用异常
    ('unknown', 500),  # 未知错误类型也触发通用异常
])
def test_error_demo_generic_error(client, error_type, expected_status):
    """测试通用异常处理"""
    url = '/api/v1/example/error-demo'
    if error_type:
        url += f'?type={error_type}'
    
    response = client.get(url)
    assert response.status_code == expected_status
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert '异常' in data['message'] 