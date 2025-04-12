#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
为essays表添加version字段的直接脚本
由于Flask-Migrate命令无法正常工作，我们使用原生SQL
"""

import os
import logging
import sqlite3
from pathlib import Path
import dotenv

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
dotenv.load_dotenv()

def get_sqlite_path():
    """获取SQLite数据库路径"""
    # 项目根目录
    base_dir = Path(__file__).resolve().parent
    
    # 数据库文件路径（在instance目录下）
    db_path = os.path.join(base_dir, 'instance', 'essay_correction.db')
    
    logger.info(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        logger.warning(f"警告: 数据库文件不存在 {db_path}")
        
    return db_path

def get_connection():
    """获取SQLite数据库连接"""
    db_path = get_sqlite_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def add_version_column(conn):
    """为essays表添加version字段"""
    try:
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='essays'")
        if not cursor.fetchone():
            logger.error("essays表不存在")
            return
        
        # 检查是否已存在version字段
        cursor.execute("PRAGMA table_info(essays)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'version' not in columns:
            logger.info("开始添加version字段到essays表")
            
            # SQLite不支持ALTER TABLE ADD COLUMN NOT NULL DEFAULT语法，需要创建临时表
            # 1. 创建临时表
            cursor.execute("""
                CREATE TABLE essays_temp AS SELECT *, 0 AS version FROM essays
            """)
            
            # 2. 删除原表
            cursor.execute("DROP TABLE essays")
            
            # 3. 重命名临时表
            cursor.execute("ALTER TABLE essays_temp RENAME TO essays")
            
            # 4. 创建索引
            cursor.execute("CREATE INDEX ix_essays_version ON essays (version)")
            
            conn.commit()
            logger.info("成功添加version字段到essays表")
        else:
            logger.info("version字段已存在于essays表中")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"添加version字段失败: {str(e)}")
        raise

def main():
    """主函数"""
    try:
        logger.info("开始执行数据库迁移")
        
        conn = get_connection()
        logger.info("成功连接到数据库")
        
        add_version_column(conn)
        
        logger.info("数据库迁移完成")
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    main() 