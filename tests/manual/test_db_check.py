import os, sqlite3
print('测试数据库连接')
db_path = os.path.join('instance', 'essay_correction.db')
print(f'数据库路径: {db_path}')
conn = sqlite3.connect(db_path)
print('连接成功!')
