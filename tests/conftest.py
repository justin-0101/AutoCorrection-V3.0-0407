#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试配置文件
定义测试环境设置和通用测试夹具(fixtures)
"""

import os
import sys
import pytest
import datetime
from pathlib import Path
import uuid
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker

# 确保app模块可以被导入
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
print(f"Python路径设置: {project_root} 已添加到sys.path")

try:
    from app import create_app
    print("成功导入app模块")
except ImportError as e:
    print(f"导入app模块失败: {e}")
    raise

try:
    from app.models.db import db as _db
    from app.models.user import User
    from app.models.membership import Membership, MembershipPlan
    from app.models.subscription import Subscription
    from app.models.essay import Essay
    print("成功导入所有必需模块")
except ImportError as e:
    print(f"导入模块失败: {e}")
    raise


@pytest.fixture(scope='session')
def app():
    """创建测试应用实例"""
    app = create_app('testing')
    
    # 建立应用上下文
    ctx = app.app_context()
    ctx.push()
    
    yield app
    
    ctx.pop()


@pytest.fixture(scope='session')
def db(app):
    """数据库fixture"""
    from app.extensions import db as _db
    
    # 在应用上下文中创建所有表
    with app.app_context():
        _db.create_all()
        
        # 创建默认角色和权限
        from app.models.user import Role, Permission
        Permission.create_default_permissions()
        Role.create_default_roles()
    
    yield _db
    
    # 清理数据库
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def session(app, db):
    """提供数据库会话 - 每个测试重置"""
    from app.extensions import db as _db
    from sqlalchemy.orm import scoped_session, sessionmaker
    
    # 开始事务
    connection = _db.engine.connect()
    transaction = connection.begin()
    
    # 创建会话
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)
    
    # 使用这个会话替换当前的
    old_session = _db.session
    _db.session = session
    
    yield session
    
    # 清理
    _db.session = old_session
    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def client(app) -> FlaskClient:
    """测试客户端"""
    return app.test_client()


@pytest.fixture
def test_user(session):
    """创建测试用户"""
    from app.models.user import User, Role, UserRole
    
    # 获取学生角色
    student_role = Role.query.filter_by(name='student').first()
    if not student_role:
        raise ValueError("学生角色未找到，请确保已创建默认角色")
    
    user = User(
        email='test@example.com',
        username='testuser',
        name='Test User',
        _is_active=True,
        is_admin=False,
        is_deleted=False
    )
    user.set_password('password123')
    
    # 添加学生角色
    user_role = UserRole(user=user, role=student_role)
    session.add(user_role)
    
    # 保存到数据库
    session.add(user)
    session.commit()
    
    return user


@pytest.fixture
def admin_user(session):
    """创建管理员用户"""
    from app.models.user import User, Role, UserRole
    
    # 获取管理员角色
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        raise ValueError("管理员角色未找到，请确保已创建默认角色")
    
    admin = User(
        email='admin@example.com',
        username='admin',
        name='Admin User',
        _is_admin=True,
        _is_active=True,
        is_deleted=False
    )
    admin.set_password('admin123')
    
    # 添加管理员角色
    user_role = UserRole(user=admin, role=admin_role)
    session.add(user_role)
    
    # 保存到数据库
    session.add(admin)
    session.commit()
    
    return admin


@pytest.fixture
def logged_in_user(app, client, session):
    """创建已登录的测试用户"""
    from flask_login import login_user
    
    # 创建测试用户
    user = User(
        username='testadmin',
        email='admin@example.com',
        is_active=True,
        is_admin=True
    )
    user.set_password('password123')  # 设置加密密码
    session.add(user)
    session.commit()
    
    # 登录用户
    with app.test_request_context():
        login_user(user)
    
    # 模拟登录状态
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['_fresh'] = True
    
    return user 