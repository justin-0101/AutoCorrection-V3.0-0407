from flask import Flask
from app import create_app
from app.models import db, User, Role, Permission

app = create_app()

def init_db():
    with app.app_context():
        # 删除所有表
        db.drop_all()
        
        # 创建所有表
        db.create_all()
        
        # 创建测试用户
        test_user = User(
            username='test',
            email='test@example.com',
            active=True,
            is_admin=False,
            is_verified=True
        )
        test_user.set_password('test123')
        
        # 创建管理员用户
        admin_user = User(
            username='admin',
            email='admin@example.com',
            active=True,
            is_admin=True,
            is_verified=True
        )
        admin_user.set_password('admin123')
        
        # 添加用户到数据库
        db.session.add(test_user)
        db.session.add(admin_user)
        
        # 提交更改
        db.session.commit()
        
        print("数据库初始化完成！")
        print("\n测试用户账号：")
        print("用户名：test")
        print("密码：test123")
        print("\n管理员账号：")
        print("用户名：admin")
        print("密码：admin123")

if __name__ == '__main__':
    init_db() 