"""
数据库迁移管理模块
"""

import os
import logging
import sqlite3
from database.db_manager import db_manager

logger = logging.getLogger(__name__)

def run_migrations():
    """运行所有迁移脚本"""
    logger.info("开始执行数据库迁移...")
    
    # 确保migration表存在（用于记录已执行的迁移）
    create_migration_table()
    
    # 获取已执行的迁移
    applied_migrations = get_applied_migrations()
    
    # 获取所有迁移脚本
    migration_dir = os.path.dirname(__file__)
    migrations = []
    
    for filename in os.listdir(migration_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            migration_name = filename[:-3]  # 去掉.py后缀
            if migration_name not in applied_migrations:
                migrations.append(migration_name)
    
    # 按文件名排序（通常采用前缀数字如001_create_users.py）
    migrations.sort()
    
    # 执行新迁移
    for migration in migrations:
        try:
            logger.info(f"执行迁移: {migration}")
            
            # 导入并执行迁移
            module = __import__(f"database.migrations.{migration}", fromlist=["upgrade"])
            module.upgrade()
            
            # 记录已执行的迁移
            record_migration(migration)
            logger.info(f"迁移 {migration} 成功执行")
        except Exception as e:
            logger.error(f"迁移 {migration} 失败: {str(e)}")
            raise
    
    logger.info(f"数据库迁移完成，共执行 {len(migrations)} 个迁移")

def create_migration_table():
    """创建迁移记录表"""
    with db_manager.get_cursor() as cursor:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration TEXT UNIQUE,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

def get_applied_migrations():
    """获取已应用的迁移列表"""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT migration FROM migrations")
            return {row['migration'] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        # 表可能不存在
        return set()

def record_migration(migration_name):
    """记录已执行的迁移"""
    with db_manager.get_cursor() as cursor:
        cursor.execute(
            "INSERT INTO migrations (migration) VALUES (?)",
            (migration_name,)
        )
