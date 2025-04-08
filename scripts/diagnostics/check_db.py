import sqlite3
import os

def check_db(db_file):
    if not os.path.exists(db_file):
        print(f"数据库文件 {db_file} 不存在")
        return
    
    print(f"\n检查数据库: {db_file}")
    print("-" * 50)
    
    # 连接到数据库
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row  # 使用Row工厂，可以通过列名访问
    cursor = conn.cursor()
    
    # 列出所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("数据库中的表:")
    for table in tables:
        print(f"- {table[0]}")
    
    # 检查是否有essays表
    if ('essays',) in tables:
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
        
        # 获取essays表的前5条记录
        print("\n查看essays表的前5条记录:")
        try:
            cursor.execute("SELECT * FROM essays LIMIT 5")
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(f"ID: {row['id']}, 标题: {row['title']}, 状态: {row.get('status', 'N/A')}")
            else:
                print("essays表中没有记录")
        except sqlite3.Error as e:
            print(f"查询essays表时出错: {e}")
    else:
        print("\n❌ 数据库中不存在essays表")
    
    # 关闭连接
    conn.close()

# 检查所有可能的数据库文件
db_files = [
    'app.db', 
    'auto_correction.db', 
    'essay_correction.db',
    'instance/essay_correction.db'
]

for db_file in db_files:
    check_db(db_file) 