import sqlite3

# 连接到数据库
conn = sqlite3.connect('instance/essay_correction.db')
cursor = conn.cursor()

# 查询所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [table[0] for table in cursor.fetchall()]
print(f"数据库中的表: {tables}")

# 检查corrections表是否存在
if 'corrections' in tables:
    print("corrections表存在")
    
    # 查看表结构
    cursor.execute("PRAGMA table_info(corrections)")
    columns = cursor.fetchall()
    print(f"corrections表结构: {columns}")
    
    # 查看表中的记录数
    cursor.execute("SELECT COUNT(*) FROM corrections")
    count = cursor.fetchone()[0]
    print(f"corrections表中有 {count} 条记录")
else:
    print("corrections表不存在！")

# 关闭连接
conn.close() 