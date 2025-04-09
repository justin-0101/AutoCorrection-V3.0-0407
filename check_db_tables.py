#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_tables(db_path):
    """检查数据库中的表"""
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n数据库 {db_path} 中的表:")
        if not tables:
            print("- 没有找到任何表")
        else:
            for table in tables:
                print(f"- {table[0]}")
                
                # 获取表的列信息
                try:
                    cursor.execute(f"PRAGMA table_info({table[0]})")
                    columns = cursor.fetchall()
                    print(f"  列信息:")
                    for col in columns:
                        print(f"    - {col[1]} ({col[2]})")
                        
                    # 获取表中的记录数
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    print(f"  记录数: {count}")
                except Exception as e:
                    print(f"  无法获取表结构: {str(e)}")
                    
    except Exception as e:
        print(f"查询数据库时出错: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # 检查主数据库
    check_tables("instance/essay_correction.db")
    
    # 检查备份
    check_tables("instance/app.db") 