import sqlite3

# 连接到数据库
conn = sqlite3.connect('instance/essay_correction.db')
cursor = conn.cursor()

# 获取表结构
cursor.execute("PRAGMA table_info(essays)")
columns = cursor.fetchall()

print("Essays表结构:")
for col in columns:
    # col包含: (序号, 名称, 类型, 是否NOT NULL, 默认值, 是否主键)
    print(f"{col[0]}: {col[1]} ({col[2]}) - 必填: {bool(col[3])} - 默认值: {col[4]}")

# 检查source_type列是否存在
has_source_type = any(col[1] == 'source_type' for col in columns)
if has_source_type:
    print("\n✅ source_type字段已成功添加到essays表中")
    
    # 显示前几条数据的source_type值
    cursor.execute("SELECT id, title, source_type FROM essays LIMIT 5")
    rows = cursor.fetchall()
    
    print("\n前5条记录的source_type值:")
    for row in rows:
        print(f"ID: {row[0]}, 标题: {row[1]}, 来源类型: {row[2]}")
else:
    print("\n❌ essays表中不存在source_type字段，迁移可能失败")

# 关闭连接
conn.close() 