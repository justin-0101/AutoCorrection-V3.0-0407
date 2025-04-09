from app import create_app
from app.models.user import User

try:
    print("创建应用...")
    app = create_app()
    print("应用创建成功")
    
    with app.app_context():
        print("查询管理员用户...")
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print('管理员信息:')
            print(f'用户名: {admin.username}')
            print(f'管理员权限: {admin.is_admin}')
            try:
                print(f'_is_admin属性: {admin._is_admin}')
            except:
                print('无法访问_is_admin属性')
            print(f'is_active: {admin.is_active}')
        else:
            print('未找到管理员用户')
except Exception as e:
    print(f"出错: {str(e)}")
    import traceback
    traceback.print_exc() 