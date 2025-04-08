#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户相关的 API 路由
"""

from flask import Blueprint, request, jsonify, current_app
from app.core.auth.auth_decorators import login_required
from app.core.auth.auth_service import AuthService
from app.core.user.user_service import UserService
from app.utils.exceptions import ValidationError, ResourceNotFoundError
from app.utils.validators import validate_user_data

user_bp = Blueprint('user', __name__)
auth_service = AuthService()
user_service = UserService()

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """获取当前用户的个人资料"""
    user = auth_service.get_current_user()
    return jsonify({
        'status': 'success',
        'data': user.to_dict()
    })

@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新当前用户的个人资料"""
    data = request.get_json()
    
    # 验证输入数据
    try:
        validate_user_data(data)
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'errors': e.errors
        }), 400
    
    user = auth_service.get_current_user()
    updated_user = user_service.update_user(user.id, data)
    
    return jsonify({
        'status': 'success',
        'message': '个人资料更新成功',
        'data': updated_user.to_dict()
    })

@user_bp.route('/password', methods=['PUT'])
@login_required
def change_password():
    """修改当前用户的密码"""
    data = request.get_json()
    
    # 验证输入数据
    if not all(k in data for k in ('old_password', 'new_password')):
        return jsonify({
            'status': 'error',
            'message': '缺少必要的参数'
        }), 400
    
    user = auth_service.get_current_user()
    
    try:
        user_service.change_password(
            user.id,
            data['old_password'],
            data['new_password']
        )
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': '密码修改成功'
    })

@user_bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    """上传用户头像"""
    if 'avatar' not in request.files:
        return jsonify({
            'status': 'error',
            'message': '没有上传文件'
        }), 400
    
    file = request.files['avatar']
    if not file.filename:
        return jsonify({
            'status': 'error',
            'message': '没有选择文件'
        }), 400
    
    user = auth_service.get_current_user()
    
    try:
        avatar_url = user_service.update_avatar(user.id, file)
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': '头像上传成功',
        'data': {
            'avatar_url': avatar_url
        }
    })

@user_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    """获取用户偏好设置"""
    user = auth_service.get_current_user()
    preferences = user_service.get_user_preferences(user.id)
    
    return jsonify({
        'status': 'success',
        'data': preferences
    })

@user_bp.route('/preferences', methods=['PUT'])
@login_required
def update_preferences():
    """更新用户偏好设置"""
    data = request.get_json()
    user = auth_service.get_current_user()
    
    try:
        preferences = user_service.update_user_preferences(user.id, data)
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': '偏好设置更新成功',
        'data': preferences
    })

@user_bp.route('/notifications/settings', methods=['GET'])
@login_required
def get_notification_settings():
    """获取通知设置"""
    user = auth_service.get_current_user()
    settings = user_service.get_notification_settings(user.id)
    
    return jsonify({
        'status': 'success',
        'data': settings
    })

@user_bp.route('/notifications/settings', methods=['PUT'])
@login_required
def update_notification_settings():
    """更新通知设置"""
    data = request.get_json()
    user = auth_service.get_current_user()
    
    try:
        settings = user_service.update_notification_settings(user.id, data)
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': '通知设置更新成功',
        'data': settings
    })

@user_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """获取用户通知列表"""
    user = auth_service.get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    notifications = user_service.get_user_notifications(
        user.id,
        page=page,
        per_page=per_page
    )
    
    return jsonify({
        'status': 'success',
        'data': notifications
    })

@user_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """标记通知为已读"""
    data = request.get_json()
    user = auth_service.get_current_user()
    
    if not data or 'notification_ids' not in data:
        return jsonify({
            'status': 'error',
            'message': '缺少必要的参数'
        }), 400
    
    user_service.mark_notifications_read(user.id, data['notification_ids'])
    
    return jsonify({
        'status': 'success',
        'message': '通知已标记为已读'
    })

@user_bp.route('/activity-log', methods=['GET'])
@login_required
def get_activity_log():
    """获取用户活动日志"""
    user = auth_service.get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    activities = user_service.get_user_activities(
        user.id,
        page=page,
        per_page=per_page
    )
    
    return jsonify({
        'status': 'success',
        'data': activities
    }) 