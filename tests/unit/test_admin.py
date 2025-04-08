import pytest
from flask import url_for
from app.models import User, UserProfile
from app.forms.admin import UpdateUserCorrectionsForm
from app.extensions import db

def test_update_user_corrections_form_validation(app):
    """测试用户批改次数更新表单的验证"""
    with app.test_request_context():
        # 测试有效数据
        form = UpdateUserCorrectionsForm(
            user_id=1,
            monthly_limit=100,
            monthly_used=50
        )
        assert form.validate() is True

        # 测试无效的月度限制（负数）
        form = UpdateUserCorrectionsForm(
            user_id=1,
            monthly_limit=-1,
            monthly_used=50
        )
        assert form.validate() is False
        assert "批改次数不能小于0" in str(form.monthly_limit.errors)

        # 测试无效的已用次数（负数）
        form = UpdateUserCorrectionsForm(
            user_id=1,
            monthly_limit=100,
            monthly_used=-1
        )
        assert form.validate() is False
        assert "已使用次数不能小于0" in str(form.monthly_used.errors)

def test_update_user_corrections_route(app, client, test_user, admin_user, session):
    """测试更新用户批改次数的路由"""
    # 检查并删除现有的profile
    if test_user.profile:
        session.delete(test_user.profile)
        session.commit()

    # 创建测试用户配置文件
    user_profile = UserProfile(
        user_id=test_user.id,
        monthly_limit=50,
        monthly_used=20
    )
    test_user.profile = user_profile
    session.add(user_profile)
    session.commit()

    # 管理员登录
    with client:
        # 登录请求
        login_response = client.post(url_for('auth.login'),
                                   data={
                                       'username': admin_user.username,
                                       'password': 'admin123'
                                   },
                                   follow_redirects=True)
        assert login_response.status_code == 200

        # 测试更新用户批改次数
        response = client.post(url_for('admin.update_user_corrections'),
                             data={
                                 'user_id': test_user.id,
                                 'monthly_limit': 100,
                                 'monthly_used': 30
                             },
                             follow_redirects=True)

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # 验证数据库中的更改
        session.refresh(test_user.profile)
        assert test_user.profile.monthly_limit == 100
        assert test_user.profile.monthly_used == 30

def test_update_user_corrections_invalid_user(app, client, admin_user, session):
    """测试更新不存在用户的批改次数"""
    # 管理员登录
    with client:
        # 登录请求
        login_response = client.post(url_for('auth.login'),
                                   data={
                                       'username': admin_user.username,
                                       'password': 'admin123'
                                   },
                                   follow_redirects=True)
        assert login_response.status_code == 200

        # 测试更新不存在的用户
        response = client.post(url_for('admin.update_user_corrections'),
                             data={
                                 'user_id': 9999,  # 不存在的用户ID
                                 'monthly_limit': 100,
                                 'monthly_used': 30
                             },
                             follow_redirects=True)

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'user not found' in data['message'].lower()

def test_update_user_corrections_unauthorized(app, client, test_user, session):
    """测试未授权用户访问更新功能"""
    # 普通用户登录
    with client:
        # 登录请求
        login_response = client.post(url_for('auth.login'),
                                   data={
                                       'username': test_user.username,
                                       'password': 'password123'
                                   },
                                   follow_redirects=True)
        assert login_response.status_code == 200

        # 测试未授权访问
        response = client.post(url_for('admin.update_user_corrections'),
                             data={
                                 'user_id': test_user.id,
                                 'monthly_limit': 100,
                                 'monthly_used': 30
                             },
                             follow_redirects=True)

        assert response.status_code == 403
        data = response.get_json()
        assert data['success'] is False
        assert 'unauthorized' in data['message'].lower() 