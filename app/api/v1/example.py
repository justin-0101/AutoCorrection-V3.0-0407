#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
示例API路由模块
展示如何使用新的统一权限检查和响应格式
"""

import logging
from flask import Blueprint, request, jsonify, g
from app.core.auth.permission_manager import permission_required, role_required, admin_required
from app.core.api import api_response, format_api_response, api_error_handler
from app.utils.exceptions import ValidationError, ResourceNotFoundError

logger = logging.getLogger(__name__)

# 创建蓝图
example_bp = Blueprint('example_api', __name__, url_prefix='/api/v1/example')

# 使用新的API响应格式
@example_bp.route('/hello', methods=['GET'])
@api_response
def hello():
    """一个简单的API示例，返回问候消息"""
    name = request.args.get('name', 'World')
    return {
        'greeting': f'Hello, {name}!',
        'message': '这是一个使用新的API响应格式的示例'
    }

# 使用自定义响应消息和状态码
@example_bp.route('/custom', methods=['GET'])
@api_response(default_message="自定义成功消息", default_status_code=201)
def custom_response():
    """使用自定义消息和状态码的API示例"""
    return {
        'custom': True,
        'note': '这个响应使用了自定义的消息和状态码'
    }

# 使用权限检查
@example_bp.route('/protected', methods=['GET'])
@permission_required('view_protected_data')
@api_response
def protected_resource():
    """需要特定权限才能访问的API"""
    return {
        'secret': '这是受保护的数据',
        'note': '你有权限查看这些数据'
    }

# 使用角色检查
@example_bp.route('/admin-only', methods=['GET'])
@role_required('admin')
@api_response
def admin_only():
    """需要管理员角色才能访问的API"""
    return {
        'admin_data': '这是管理员数据',
        'note': '只有管理员才能看到这些数据'
    }

# 使用简化的管理员检查
@example_bp.route('/admin-shortcut', methods=['GET'])
@admin_required
@api_response
def admin_shortcut():
    """使用简化语法的管理员专用API"""
    return {
        'admin_data': '这是管理员数据',
        'note': '使用简化的@admin_required装饰器'
    }

# 使用错误处理
@example_bp.route('/error-demo', methods=['GET'])
@api_error_handler
def error_demo():
    """演示错误处理的API"""
    error_type = request.args.get('type', 'generic')
    
    if error_type == 'validation':
        raise ValidationError("数据验证失败", errors={
            'field1': ['不能为空'],
            'field2': ['格式不正确']
        })
    elif error_type == 'not_found':
        raise ResourceNotFoundError("请求的资源不存在")
    elif error_type == 'custom':
        # 使用format_api_response手动构建错误响应
        return format_api_response(
            message="自定义错误消息",
            status_code=400,
            errors={"custom_error": ["这是一个自定义错误"]},
            error_code="CUSTOM_ERROR"
        )
    else:
        # 触发一个通用异常
        raise Exception("这是一个未处理的异常")

# 使用基于资源的权限检查
@example_bp.route('/resource/<int:resource_id>', methods=['GET'])
@permission_required('view_resource', resource_loader=lambda resource_id, **kwargs: {'id': resource_id, 'type': 'example'})
@api_response
def get_resource(resource_id):
    """
    使用基于资源的权限检查的API
    resource_loader函数负责加载要检查权限的资源
    """
    # 在实际应用中，这里会从数据库加载资源
    resource = {
        'id': resource_id,
        'name': f'Resource {resource_id}',
        'description': '这是一个受保护的资源'
    }
    
    return resource

# 注册蓝图函数（根据需要在app/__init__.py中调用）
def register_example_blueprint(app):
    """注册示例API蓝图"""
    from app.core.api import register_api_blueprint
    register_api_blueprint(example_bp)
    app.register_blueprint(example_bp)
    logger.info("已注册示例API蓝图")
    return example_bp 