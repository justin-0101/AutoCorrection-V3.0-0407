#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建管理员用户脚本
"""

from app import create_app, db
from app.models.user import User

def create_admin():
    """创建一个管理员用户，如果不存在"""
    app = create_app()
    with app.app_context():
        # 检查用户是否已存在
        existing_user = User.query.filter_by(username='admin').first()
        if existing_user:
            print('管理员用户已存在')
            return
        
        # 创建新用户
        user = User(username='admin', email='admin@example.com')
        user.set_password('admin123')
        user.is_admin = True
        db.session.add(user)
        db.session.commit()
        print('管理员用户已创建：admin/admin123')

if __name__ == '__main__':
    create_admin() 