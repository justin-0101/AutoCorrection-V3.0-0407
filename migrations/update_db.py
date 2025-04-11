#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接更新SQLite数据库脚本
"""

import sqlite3
import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库文件路径
DB_PATH = "instance/essay_correction.db"

def execute_sql_directly():
    """直接执行SQL命令更新数据库"""
    
    if not os.path.exists(DB_PATH):
        logger.error(f"数据库文件不存在: {DB_PATH}")
        return False
    
    try:
        logger.info(f"尝试连接到数据库: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 修改essays表约束的Pragma命令
        logger.info("检查essays表的结构...")
        cursor.execute("PRAGMA table_info(essays)")
        columns = cursor.fetchall()
        for col in columns:
            logger.info(f"列: {col}")
        
        # 修改corrections表约束的Pragma命令
        logger.info("检查corrections表的结构...")
        cursor.execute("PRAGMA table_info(corrections)")
        columns = cursor.fetchall()
        for col in columns:
            logger.info(f"列: {col}")
        
        # 创建新临时表
        logger.info("创建临时表...")
        try:
            # 检查临时表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='__temp_essays'")
            if cursor.fetchone():
                cursor.execute("DROP TABLE __temp_essays")
                
            # 创建essays临时表
            cursor.execute("""
            CREATE TABLE __temp_essays AS 
            SELECT * FROM essays
            """)
        
            # 删除原essays表
            cursor.execute("DROP TABLE essays")
            
            # 创建新essays表，带有更新的约束
            cursor.execute("""
            CREATE TABLE essays (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                word_count INTEGER,
                user_id INTEGER NOT NULL,
                author_name VARCHAR(100),
                status VARCHAR(20),
                score FLOAT,
                corrected_at DATETIME,
                error_message TEXT,
                grade VARCHAR(50),
                source_type VARCHAR(20) NOT NULL,
                corrected_content TEXT,
                comments TEXT,
                error_analysis TEXT,
                improvement_suggestions TEXT,
                ai_score FLOAT,
                ai_comments TEXT,
                ai_analysis TEXT,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                correction_count INTEGER,
                is_public BOOLEAN,
                is_deleted BOOLEAN,
                created_at DATETIME,
                updated_at DATETIME,
                CONSTRAINT valid_source_type CHECK (source_type IN ('text', 'paste', 'upload', 'api')),
                CONSTRAINT valid_status CHECK (status IN ('draft', 'pending', 'processing', 'correcting', 'completed', 'failed', 'archived')),
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """)
            
            # 复制essays数据
            cursor.execute("INSERT INTO essays SELECT * FROM __temp_essays")
            
            # 删除essays临时表
            cursor.execute("DROP TABLE __temp_essays")
            logger.info("Essays表约束更新完成")
        except Exception as e:
            logger.error(f"更新essays表时出错: {str(e)}")
            conn.rollback()
            
        try:
            # 检查临时表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='__temp_corrections'")
            if cursor.fetchone():
                cursor.execute("DROP TABLE __temp_corrections")
                
            # 创建corrections临时表
            cursor.execute("""
            CREATE TABLE __temp_corrections AS 
            SELECT * FROM corrections
            """)
        
            # 删除原corrections表
            cursor.execute("DROP TABLE corrections")
            
            # 创建新corrections表，带有更新的约束
            cursor.execute("""
            CREATE TABLE corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                essay_id INTEGER NOT NULL,
                corrector_id INTEGER,
                type VARCHAR(20) NOT NULL,
                content TEXT,
                score FLOAT,
                comments TEXT,
                error_analysis TEXT,
                improvement_suggestions TEXT,
                extra_data TEXT,
                status VARCHAR(20) NOT NULL,
                results TEXT,
                task_id VARCHAR(36),
                error_message TEXT,
                retry_count INTEGER,
                created_at DATETIME,
                updated_at DATETIME,
                completed_at DATETIME,
                is_deleted BOOLEAN NOT NULL,
                CONSTRAINT valid_correction_type CHECK (type IN ('ai', 'human')),
                CONSTRAINT valid_correction_status CHECK (status IN ('pending', 'processing', 'correcting', 'completed', 'failed')),
                FOREIGN KEY(corrector_id) REFERENCES users (id) ON DELETE SET NULL,
                FOREIGN KEY(essay_id) REFERENCES essays (id) ON DELETE CASCADE,
                UNIQUE (task_id)
            )
            """)
            
            # 复制corrections数据
            cursor.execute("INSERT INTO corrections SELECT * FROM __temp_corrections")
            
            # 删除corrections临时表
            cursor.execute("DROP TABLE __temp_corrections")
            logger.info("Corrections表约束更新完成")
        except Exception as e:
            logger.error(f"更新corrections表时出错: {str(e)}")
            conn.rollback()
        
        # 提交事务
        conn.commit()
        logger.info("数据库更新完成，事务已提交")
        
        # 关闭连接
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"执行SQL命令时出错: {str(e)}")
        return False

if __name__ == "__main__":
    result = execute_sql_directly()
    if result:
        logger.info("数据库更新成功！")
        sys.exit(0)
    else:
        logger.error("数据库更新失败！")
        sys.exit(1) 