import os
import sqlite3

print("=== 检查管理员账户状态 ===")
# 连接数据库
conn = sqlite3.connect('instance/essay_correction.db')
cursor = conn.cursor()

# 检查juschen账户信息
cursor.execute("SELECT user_id, username, role FROM users WHERE username = 'juschen'")
user = cursor.fetchone()

if user:
    user_id, username, role = user
    print(f"找到用户: ID={user_id}, 用户名={username}, 角色={role}")
    
    # 如果不是admin，则修改为admin
    if role != 'admin':
        cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'juschen'")
        conn.commit()
        print("已将juschen用户角色更新为admin")
        
        # 再次查询确认更新成功
        cursor.execute("SELECT user_id, username, role FROM users WHERE username = 'juschen'")
        updated_user = cursor.fetchone()
        print(f"更新后用户信息: ID={updated_user[0]}, 用户名={updated_user[1]}, 角色={updated_user[2]}")
    else:
        print("该用户已经是admin角色，无需更新")
else:
    print("未找到juschen用户")

# 检查session中的角色信息
print("\n=== 检查模板文件 ===")
template_paths = [
    'templates/admin',
    'templates/admin/dashboard.html',
    'templates/admin/layout.html',
    'templates/admin/user_management.html',
    'templates/admin/website_config.html',
    'templates/admin/essay_stats.html',
    'templates/admin/log_viewer.html',
    'templates/admin/order_management.html'
]

for path in template_paths:
    if os.path.exists(path):
        file_type = "目录" if os.path.isdir(path) else "文件"
        print(f"{file_type} {path} 存在")
    else:
        print(f"错误: {path} 不存在!")

# 关闭连接
conn.close()

print("\n=== 检查完成 ===")
print("如果用户角色已设置为admin且模板文件存在，但仍然无法访问管理后台，")
print("可能是路由处理或session问题，建议尝试重新登录后访问 /admin/dashboard") 