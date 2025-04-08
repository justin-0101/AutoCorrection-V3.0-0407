from flask import Flask
from app import create_app
from app.models import User

app = create_app()

with app.app_context():
    users = User.query.all()
    print("\n=== 用户列表 ===")
    if not users:
        print("数据库中没有用户记录")
    else:
        for user in users:
            print(f"ID: {user.id}")
            print(f"用户名: {user.username}")
            print(f"邮箱: {user.email}")
            print(f"是否激活: {user.is_active}")
            print("-" * 20) 