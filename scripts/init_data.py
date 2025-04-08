#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
初始化数据脚本
创建默认的角色、权限和管理员用户
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask
from app import create_app
from app.models import db, User, Role, Permission, UserRole, RolePermission

def init_db(app):
    """初始化数据库"""
    print("Initializing database...")
    with app.app_context():
        db.create_all()

def init_permissions():
    """创建默认权限"""
    print("Creating default permissions...")
    default_permissions = [
        ('all', '所有权限'),
        ('manage_essays', '管理作文'),
        ('view_reports', '查看报告'),
        ('manage_own_essays', '管理自己的作文'),
        ('view_own_reports', '查看自己的报告'),
        ('manage_users', '管理用户'),
        ('manage_own_students', '管理自己的学生'),
        ('view_public_content', '查看公开内容'),
        ('manage_system', '管理系统'),
        ('manage_roles', '管理角色'),
        ('manage_permissions', '管理权限')
    ]
    
    permissions = {}
    for name, description in default_permissions:
        permission = Permission.query.filter_by(name=name).first()
        if not permission:
            permission = Permission(name=name, description=description)
            db.session.add(permission)
            print(f"Created permission: {name}")
        permissions[name] = permission
    
    db.session.commit()
    return permissions

def init_roles(permissions):
    """创建默认角色"""
    print("\nCreating default roles...")
    roles = {
        'admin': ['all'],
        'teacher': ['manage_essays', 'view_reports', 'manage_own_students'],
        'student': ['manage_own_essays', 'view_own_reports'],
        'guest': ['view_public_content']
    }
    
    created_roles = {}
    for role_name, permission_names in roles.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f'{role_name} role')
            db.session.add(role)
            print(f"Created role: {role_name}")
        
        # 添加权限
        for perm_name in permission_names:
            if perm_name in permissions:
                perm = permissions[perm_name]
                if not role.has_permission(perm.name):
                    role_perm = RolePermission(role=role, permission=perm)
                    db.session.add(role_perm)
                    print(f"Added permission {perm_name} to role {role_name}")
        
        created_roles[role_name] = role
    
    db.session.commit()
    return created_roles

def create_admin_user(admin_role):
    """创建管理员用户"""
    print("\nCreating admin user...")
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            name='System Administrator',
            is_admin=True,
            is_active=True,
            is_verified=True,
            membership_level='premium',
            membership_expires=datetime.now() + timedelta(days=3650)  # 10年会员期
        )
        admin.set_password('admin123')  # 设置默认密码
        db.session.add(admin)
        print("Created admin user")
        
        # 添加管理员角色
        user_role = UserRole(user=admin, role=admin_role)
        db.session.add(user_role)
        print("Added admin role to admin user")
        
        db.session.commit()
    return admin

def init_data(app):
    """初始化所有数据"""
    with app.app_context():
        print("Starting data initialization...")
        
        # 初始化数据库
        init_db(app)
        
        # 创建权限
        permissions = init_permissions()
        
        # 创建角色
        roles = init_roles(permissions)
        
        # 创建管理员用户
        admin = create_admin_user(roles['admin'])
        
        print("\nData initialization completed!")
        print(f"Admin user created with username: admin and password: admin123")

if __name__ == '__main__':
    app = create_app()
    init_data(app) 