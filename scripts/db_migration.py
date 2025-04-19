#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接修改数据库结构的脚本，用于删除essay表中的file_path和file_name列
"""

import os
import sys
import logging
import sqlite3
from sqlalchemy import create_engine, text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_migration')

# 确保运行路径是项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

def get_database_uri():
    """获取数据库URI"""
    # 从环境变量获取数据库URI
    database_uri = os.environ.get('DATABASE_URI')
    
    # 如果环境变量中没有设置，使用默认SQLite数据库
    if not database_uri:
        sqlite_db_path = os.path.join(project_root, 'instance', 'autocorrection.db')
        database_uri = f'sqlite:///{sqlite_db_path}'
        
    return database_uri

def drop_columns_with_sqlalchemy():
    """使用SQLAlchemy删除列"""
    try:
        # 获取数据库URI
        database_uri = get_database_uri()
        logger.info(f"连接到数据库: {database_uri}")
        
        # 创建引擎
        engine = create_engine(database_uri)
        
        # 检查列是否存在
        with engine.connect() as conn:
            # 获取essay表的结构
            result = conn.execute(text("PRAGMA table_info(essay)"))
            columns = result.fetchall()
            
            # 检查file_path和file_name列是否存在
            has_file_path = any(col[1] == 'file_path' for col in columns)
            has_file_name = any(col[1] == 'file_name' for col in columns)
            
            if not has_file_path and not has_file_name:
                logger.info("file_path和file_name列已经不存在，无需删除")
                return
            
            logger.info(f"essay表中的列: {[col[1] for col in columns]}")
            
            # 创建临时表
            logger.info("创建临时表...")
            column_defs = []
            column_names = []
            
            for col in columns:
                col_name = col[1]
                if col_name not in ['file_path', 'file_name']:
                    col_type = col[2]
                    not_null = "NOT NULL" if col[3] == 1 else ""
                    default = f"DEFAULT {col[4]}" if col[4] is not None else ""
                    pk = "PRIMARY KEY" if col[5] == 1 else ""
                    
                    column_defs.append(f"{col_name} {col_type} {not_null} {default} {pk}".strip())
                    column_names.append(col_name)
            
            # 创建临时表
            conn.execute(text(f"""
                CREATE TABLE essay_temp (
                    {', '.join(column_defs)}
                )
            """))
            
            # 复制数据
            logger.info("复制数据到临时表...")
            conn.execute(text(f"""
                INSERT INTO essay_temp ({', '.join(column_names)})
                SELECT {', '.join(column_names)} FROM essay
            """))
            
            # 删除原表
            logger.info("删除原表...")
            conn.execute(text("DROP TABLE essay"))
            
            # 重命名临时表
            logger.info("重命名临时表...")
            conn.execute(text("ALTER TABLE essay_temp RENAME TO essay"))
            
            # 提交事务
            conn.commit()
            
            logger.info("列删除成功")
    
    except Exception as e:
        logger.error(f"删除列时出错: {str(e)}")
        raise

def drop_columns_with_sqlite():
    """使用SQLite命令删除列"""
    try:
        # 获取SQLite数据库路径
        database_uri = get_database_uri()
        if database_uri.startswith('sqlite:///'):
            sqlite_db_path = database_uri[10:]
        else:
            logger.error("不支持的数据库类型，仅支持SQLite")
            return
        
        logger.info(f"连接到SQLite数据库: {sqlite_db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(sqlite_db_path)
        cursor = conn.cursor()
        
        # 获取essay表的结构
        cursor.execute("PRAGMA table_info(essay)")
        columns = cursor.fetchall()
        
        # 检查file_path和file_name列是否存在
        has_file_path = any(col[1] == 'file_path' for col in columns)
        has_file_name = any(col[1] == 'file_name' for col in columns)
        
        if not has_file_path and not has_file_name:
            logger.info("file_path和file_name列已经不存在，无需删除")
            conn.close()
            return
        
        logger.info(f"essay表中的列: {[col[1] for col in columns]}")
        
        # 开始事务
        conn.execute("BEGIN TRANSACTION")
        
        # 创建临时表
        column_defs = []
        column_names = []
        
        for col in columns:
            col_name = col[1]
            if col_name not in ['file_path', 'file_name']:
                col_type = col[2]
                not_null = "NOT NULL" if col[3] == 1 else ""
                default = f"DEFAULT {col[4]}" if col[4] is not None else ""
                pk = "PRIMARY KEY" if col[5] == 1 else ""
                
                column_defs.append(f"{col_name} {col_type} {not_null} {default} {pk}".strip())
                column_names.append(col_name)
        
        # 创建临时表
        logger.info("创建临时表...")
        cursor.execute(f"""
            CREATE TABLE essay_temp (
                {', '.join(column_defs)}
            )
        """)
        
        # 复制数据
        logger.info("复制数据到临时表...")
        cursor.execute(f"""
            INSERT INTO essay_temp ({', '.join(column_names)})
            SELECT {', '.join(column_names)} FROM essay
        """)
        
        # 删除原表
        logger.info("删除原表...")
        cursor.execute("DROP TABLE essay")
        
        # 重命名临时表
        logger.info("重命名临时表...")
        cursor.execute("ALTER TABLE essay_temp RENAME TO essay")
        
        # 提交事务
        conn.commit()
        logger.info("列删除成功")
        
        # 关闭连接
        conn.close()
    
    except Exception as e:
        logger.error(f"删除列时出错: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("开始数据库迁移...")
    
    try:
        # 尝试使用SQLAlchemy删除列
        drop_columns_with_sqlalchemy()
    except Exception as e:
        logger.warning(f"使用SQLAlchemy删除列失败: {str(e)}")
        logger.info("尝试使用SQLite命令删除列...")
        drop_columns_with_sqlite()
    
    logger.info("数据库迁移完成") 