from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f'管理员 {admin.username} 当前权限状态: is_admin={admin.is_admin}')
        
        # 更新管理员权限
        admin.is_admin = True
        db.session.commit()
        
        # 重新查询确认更新成功
        admin = User.query.filter_by(username='admin').first()
        print(f'管理员 {admin.username} 权限已更新: is_admin={admin.is_admin}')
    else:
        print('未找到管理员用户') 