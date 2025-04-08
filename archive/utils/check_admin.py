import sqlite3

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

# 关闭连接
conn.close() 