import sqlite3
conn = sqlite3.connect('instance/essay_correction.db')
cursor = conn.cursor()

# 更新juschen的角色为admin
cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'juschen'")
conn.commit()
print('已将juschen设置为管理员')

# 验证更新
cursor.execute('SELECT user_id, username, role FROM users')
results = cursor.fetchall()
print(results)

conn.close() 