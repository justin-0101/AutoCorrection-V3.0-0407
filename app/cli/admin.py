#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click
from flask.cli import with_appcontext
from app.models import db, User, Role, Permission, UserRole, RolePermission

@click.group()
def admin():
    """管理员命令组"""
    pass

@admin.command()
@click.argument('username')
@with_appcontext
def make_admin(username):
    """将用户设置为管理员"""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f'用户 {username} 不存在')
        return
    
    # 设置管理员标志
    user._is_admin = True
    
    # 获取或创建管理员角色
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='管理员角色')
        db.session.add(admin_role)
        
        # 创建所有权限
        all_permission = Permission.query.filter_by(name='all').first()
        if not all_permission:
            all_permission = Permission(name='all', description='所有权限')
            db.session.add(all_permission)
            
        # 为管理员角色添加所有权限
        role_perm = RolePermission(role=admin_role, permission=all_permission)
        db.session.add(role_perm)
    
    # 为用户添加管理员角色
    if not any(ur.role.name == 'admin' for ur in user.user_roles):
        user_role = UserRole(user=user, role=admin_role)
        db.session.add(user_role)
    
    try:
        db.session.commit()
        click.echo(f'已将用户 {username} 设置为管理员')
    except Exception as e:
        db.session.rollback()
        click.echo(f'设置管理员失败: {str(e)}')

@admin.command()
@click.argument('username')
@with_appcontext
def revoke_admin(username):
    """撤销用户的管理员权限"""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f'用户 {username} 不存在')
        return
    
    # 移除管理员标志
    user._is_admin = False
    
    # 移除管理员角色
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        user_role = UserRole.query.filter_by(user=user, role=admin_role).first()
        if user_role:
            db.session.delete(user_role)
    
    try:
        db.session.commit()
        click.echo(f'已撤销用户 {username} 的管理员权限')
    except Exception as e:
        db.session.rollback()
        click.echo(f'撤销管理员权限失败: {str(e)}')

@admin.command()
@with_appcontext
def init_permissions():
    """初始化权限和角色"""
    # 创建默认权限
    Permission.create_default_permissions()
    
    # 创建默认角色
    Role.create_default_roles()
    
    click.echo('权限和角色初始化完成')

@admin.command()
@with_appcontext
def list_admins():
    """列出所有管理员"""
    admins = User.query.filter_by(_is_admin=True).all()
    if not admins:
        click.echo('没有管理员用户')
        return
        
    for admin in admins:
        click.echo(f'用户名: {admin.username}, ID: {admin.id}, 邮箱: {admin.email}') 