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
    return app


@pytest.fixture(scope='session')
def db(app):
    """创建数据库实例"""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture(scope='function')
def session(db):
    """创建数据库会话"""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # 创建会话工厂
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)
    
    # 替换当前会话
    old_session = db.session
    db.session = session
    
    yield session
    
    # 清理
    session.remove()
    transaction.rollback()
    connection.close()
    db.session = old_session


@pytest.fixture
def client(app) -> FlaskClient:
    """测试客户端"""
    return app.test_client()


@pytest.fixture
def test_user(app, session):
    """创建测试用户"""
    user = User(
        username='test_user',
        email='test@example.com',
        is_active=True
    )
    user.set_password('test123')  # 设置测试密码
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