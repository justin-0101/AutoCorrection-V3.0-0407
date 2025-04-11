#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
from pathlib import Path

def check_database(db_path):
    """检查SQLite数据库连接和表结构"""
    print(f"检查数据库: {db_path}")
    print(f"文件存在: {os.path.exists(db_path)}")
    print(f"文件大小: {os.path.getsize(db_path)} 字节")
    
    try:
        # 尝试连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n数据库中的表 ({len(tables)}):")
        for table in tables:
            table_name = table[0]
            print(f"- {table_name}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"  列数: {len(columns)}")
            
            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            print(f"  行数: {row_count}")
            
            if row_count > 0 and table_name == 'essay':
                # 显示最近的5条记录
                cursor.execute(f"SELECT id, status, created_at FROM {table_name} ORDER BY created_at DESC LIMIT 5")
                recent_rows = cursor.fetchall()
                print(f"  最近的记录:")
                for row in recent_rows:
                    print(f"    ID: {row[0]}, 状态: {row[1]}, 创建时间: {row[2]}")
            
            print()
            
        conn.close()
        print("数据库连接成功并正常关闭")
        return True
    except sqlite3.Error as e:
        print(f"SQLite错误: {e}")
        return False
    except Exception as e:
        print(f"发生错误: {e}")
        return False

if __name__ == "__main__":
    # 检查两个数据库文件
    instance_dir = Path("instance")
    
    app_db = instance_dir / "app.db"
    essay_db = instance_dir / "essay_correction.db"
    
    print("=" * 50)
    print("检查 app.db (符号链接)")
    print("=" * 50)
    check_database(app_db)
    
    print("\n" + "=" * 50)
    print("检查 essay_correction.db (实际数据库)")
    print("=" * 50)
    check_database(essay_db) 