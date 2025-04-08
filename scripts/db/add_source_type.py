#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接修改SQLite数据库添加source_type字段
这是一个临时解决方案，用于解决SQLite迁移问题
"""

import sqlite3
import os

def add_source_type_column():
    """添加source_type列到essays表"""
    # 确认数据库文件存在
    db_file = 'essay_correction.db'
    if not os.path.exists(db_file):
        print(f"错误：找不到数据库文件 {db_file}")
        return False
    
    # 备份数据库
    backup_file = f"{db_file}.bak2"
    if not os.path.exists(backup_file):
        print(f"创建备份 {backup_file}...")
        import shutil
        shutil.copy2(db_file, backup_file)
    
    # 连接数据库
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='essays'")
        if not cursor.fetchone():
            print("错误：essays表不存在")
            conn.close()
            return False
        
        # 检查source_type列是否已存在
        cursor.execute("PRAGMA table_info(essays)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'source_type' in columns:
            print("source_type列已存在，无需添加")
            conn.close()
            return True
        
        print("开始添加source_type列...")
        
        # 由于SQLite的限制，我们需要通过创建新表的方式来添加NOT NULL列
        
        # 1. 获取当前表的结构
        cursor.execute("PRAGMA table_info(essays)")
        columns_info = cursor.fetchall()
        columns_def = []
        for col in columns_info:
            col_name = col[1]
            col_type = col[2]
            col_notnull = "NOT NULL" if col[3] else ""
            col_default = f"DEFAULT {col[4]}" if col[4] is not None else ""
            col_pk = "PRIMARY KEY" if col[5] else ""
            columns_def.append(f"{col_name} {col_type} {col_notnull} {col_default} {col_pk}".strip())
        
        # 2. 获取外键约束
        cursor.execute("PRAGMA foreign_key_list(essays)")
        fk_constraints = cursor.fetchall()
        fk_defs = []
        for fk in fk_constraints:
            fk_defs.append(f"FOREIGN KEY({fk[3]}) REFERENCES {fk[2]}({fk[4]})")
        
        # 3. 创建新表，包含source_type列
        columns_def.append("source_type VARCHAR(20) NOT NULL DEFAULT 'text'")
        create_table_sql = f"""
        CREATE TABLE essays_new (
            {', '.join(columns_def)}
            {', ' + ', '.join(fk_defs) if fk_defs else ''}
        )
        """
        cursor.execute(create_table_sql)
        
        # 4. 复制数据
        cursor.execute(f"PRAGMA table_info(essays)")
        old_columns = [col[1] for col in cursor.fetchall()]
        cursor.execute(f"INSERT INTO essays_new ({', '.join(old_columns)}) SELECT {', '.join(old_columns)} FROM essays")
        
        # 5. 删除旧表，重命名新表
        cursor.execute("DROP TABLE essays")
        cursor.execute("ALTER TABLE essays_new RENAME TO essays")
        
        # 6. 创建必要的索引
        cursor.execute("CREATE INDEX ix_essays_id ON essays (id)")
        
        # 提交更改
        conn.commit()
        print("成功添加source_type列")
        
        # 关闭连接
        conn.close()
        return True
        
    except Exception as e:
        print(f"错误：{str(e)}")
        # 尝试关闭连接
        try:
            conn.close()
        except:
            pass
        return False

if __name__ == "__main__":
    if add_source_type_column():
        print("脚本执行成功")
    else:
        print("脚本执行失败") 