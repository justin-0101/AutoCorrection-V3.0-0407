#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复essays表中的version列
当version列存在但类型出错时，重建该列
"""

import sqlite3
import os
from pathlib import Path

def fix_version_column():
    # 数据库文件路径
    db_path = Path("instance/essay_correction.db")
    
    if not db_path.exists():
        print(f"错误：数据库文件不存在 {db_path}")
        return False
    
    print(f"连接数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查列类型
        cursor.execute("PRAGMA table_info(essays)")
        columns = cursor.fetchall()
        has_version = False
        version_type_correct = False
        
        for col in columns:
            if col[1] == 'version':
                has_version = True
                if col[2]:  # 如果类型不为空
                    version_type_correct = True
                print(f"找到version列, 类型: '{col[2]}'")
                
        if not has_version:
            print("version列不存在，无需修复")
            return True
            
        if version_type_correct:
            print("version列类型正确，无需修复")
            return True
        
        print("开始修复version列")
        
        # 检查临时表是否存在并删除
        print("检查并删除可能存在的临时表")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='essays_temp'")
        if cursor.fetchone():
            print("临时表已存在，先删除")
            cursor.execute("DROP TABLE essays_temp")
        
        # 1. 创建临时表
        print("1. 创建临时表")
        cursor.execute("""
        CREATE TABLE essays_temp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, 
            content TEXT,
            word_count INTEGER,
            user_id INTEGER,
            author_name TEXT,
            status TEXT,
            score REAL,
            corrected_at TIMESTAMP,
            error_message TEXT,
            grade TEXT,
            source_type TEXT,
            corrected_content TEXT,
            comments TEXT,
            error_analysis TEXT,
            improvement_suggestions TEXT,
            ai_score REAL,
            ai_comments TEXT,
            ai_analysis TEXT,
            view_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            correction_count INTEGER DEFAULT 0,
            is_public BOOLEAN DEFAULT 0,
            is_deleted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            version INTEGER DEFAULT 0 NOT NULL
        )
        """)
        
        # 2. 复制数据
        print("2. 复制数据到临时表")
        cursor.execute("""
        INSERT INTO essays_temp 
        SELECT id, title, content, word_count, user_id, author_name, status, score, 
               corrected_at, error_message, grade, source_type, corrected_content, 
               comments, error_analysis, improvement_suggestions, ai_score, ai_comments, 
               ai_analysis, view_count, like_count, comment_count, correction_count, 
               is_public, is_deleted, created_at, updated_at, 0 
        FROM essays
        """)
        
        # 3. 删除原表
        print("3. 删除原表")
        cursor.execute("DROP TABLE essays")
        
        # 4. 重命名临时表
        print("4. 重命名临时表为essays")
        cursor.execute("ALTER TABLE essays_temp RENAME TO essays")
        
        # 5. 创建索引
        print("5. 创建索引")
        cursor.execute("CREATE INDEX ix_essays_version ON essays(version)")
        
        # 提交更改
        conn.commit()
        print("修复完成！essays表的version列已修复")
        
        # 验证修复
        cursor.execute("PRAGMA table_info(essays)")
        columns = cursor.fetchall()
        for col in columns:
            if col[1] == 'version':
                print(f"验证：version列现在的类型是 '{col[2]}'")
                
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"修复过程中出错: {str(e)}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    fix_version_column() 