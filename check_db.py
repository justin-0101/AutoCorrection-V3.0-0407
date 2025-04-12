#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os

print("脚本开始执行...")

# 获取数据库路径
db_path = os.path.join('instance', 'essay_correction.db')
print(f"数据库路径: {db_path}")
print(f"数据库文件存在: {os.path.exists(db_path)}")

# 连接到数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 打印所有表
print("\n数据库中的表:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"- {table[0]}")

# 检查essays表
print("\nEssays表结构:")
cursor.execute("PRAGMA table_info(essays)")
columns = cursor.fetchall()
for col in columns:
    print(f"- {col[1]} ({col[2]})")

# 检查索引
print("\nEssays表索引:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='essays'")
indexes = cursor.fetchall()
for idx in indexes:
    print(f"- {idx[0]}")

# 检查version字段
has_version = any(col[1] == 'version' for col in columns)
print(f"\nVersion字段已添加: {'是' if has_version else '否'}")

# 检查version索引
has_version_index = any(idx[0] == 'ix_essays_version' for idx in indexes)
print(f"Version索引已添加: {'是' if has_version_index else '否'}")

# 关闭连接
conn.close()

print("\n脚本执行完成。") 