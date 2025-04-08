import sqlite3
import os

db_file = 'instance/essay_correction.db'

if not os.path.exists(db_file):
    print(f"数据库文件 {db_file} 不存在")
    exit(1)

# 连接到数据库
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 确认essays表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='essays';")
table_exists = cursor.fetchone()
if not table_exists:
    print("essays表不存在")
    
    # 列出所有存在的表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("数据库中存在以下表:")
    for table in tables:
        print(f"- {table[0]}")
    
    conn.close()
    exit(1)

# 查看表结构
print("\nessays表结构:")
cursor.execute("PRAGMA table_info(essays)")
columns = cursor.fetchall()
for col in columns:
    print(f"{col[0]}: {col[1]} ({col[2]}) - 必填: {bool(col[3])} - 默认值: {col[4]}")

# 检查是否有source_type列
has_source_type = any(col[1] == 'source_type' for col in columns)
if has_source_type:
    print("\n✅ essays表中存在source_type列")
else:
    print("\n❌ essays表中不存在source_type列")

# 获取表中的记录数
cursor.execute("SELECT COUNT(*) FROM essays")
count = cursor.fetchone()[0]
print(f"\n表中共有 {count} 条记录")

# 查看前几条记录
if count > 0:
    print("\n表中的前5条记录:")
    cursor.execute("SELECT * FROM essays LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}, 标题: {row[1]}")

# 关闭连接
conn.close() 