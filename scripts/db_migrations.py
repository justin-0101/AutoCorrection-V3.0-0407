#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库迁移脚本
提供数据库表结构初始化和版本升级功能
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

# 设置项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.config.app_config import APP_CONFIG
from app.utils.db_manager import db_manager

# 配置日志
logger = logging.getLogger(__name__)

# 数据库迁移版本列表
MIGRATIONS = [
    {
        'version': 1,
        'description': '初始化数据库结构',
        'scripts': [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(64) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            """,
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                full_name VARCHAR(100),
                school VARCHAR(100),
                grade VARCHAR(20),
                subscription_expires TIMESTAMP,
                essay_count INTEGER DEFAULT 0,
                essay_monthly_limit INTEGER DEFAULT 5,
                essay_monthly_used INTEGER DEFAULT 0,
                reset_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS essays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title VARCHAR(100) NOT NULL,
                original_text TEXT NOT NULL,
                corrected_text TEXT,
                word_count INTEGER,
                submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_time FLOAT,
                grade VARCHAR(20),
                scores_json TEXT,
                feedback_json TEXT,
                errors_json TEXT,
                suggestions_json TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_essays_user_id ON essays(user_id);
            CREATE INDEX IF NOT EXISTS idx_essays_submission_time ON essays(submission_time);
            """,
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan VARCHAR(20) NOT NULL,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                payment_id VARCHAR(100),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
            """,
            """
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id);
            """,
            """
            CREATE TABLE IF NOT EXISTS db_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );
            """
        ]
    },
    # 在这里添加后续版本的迁移脚本...
    {
        'version': 2,
        'description': '添加作文统计表',
        'scripts': [
            """
            CREATE TABLE IF NOT EXISTS essay_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                essay_id INTEGER NOT NULL UNIQUE,
                total_errors INTEGER DEFAULT 0,
                grammar_errors INTEGER DEFAULT 0,
                spelling_errors INTEGER DEFAULT 0,
                punctuation_errors INTEGER DEFAULT 0,
                structure_errors INTEGER DEFAULT 0,
                content_errors INTEGER DEFAULT 0,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (essay_id) REFERENCES essays(id) ON DELETE CASCADE
            );
            """
        ]
    }
]

def get_current_db_version():
    """获取当前数据库版本"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # 检查版本表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_version'")
        if not cursor.fetchone():
            return 0
        
        # 获取最新版本
        cursor.execute("SELECT MAX(version) FROM db_version")
        version = cursor.fetchone()[0]
        return version or 0
    except Exception as e:
        logger.error(f"获取数据库版本失败: {str(e)}")
        return 0

def run_migrations():
    """运行数据库迁移"""
    current_version = get_current_db_version()
    logger.info(f"当前数据库版本: {current_version}")
    
    # 获取需要运行的迁移
    pending_migrations = [m for m in MIGRATIONS if m['version'] > current_version]
    
    if not pending_migrations:
        logger.info("数据库已是最新版本，无需迁移")
        return True
    
    # 按版本排序
    pending_migrations.sort(key=lambda x: x['version'])
    
    try:
        conn = db_manager.get_connection()
        
        for migration in pending_migrations:
            version = migration['version']
            description = migration['description']
            logger.info(f"开始迁移到版本 {version}: {description}")
            
            # 开始事务
            conn.execute("BEGIN TRANSACTION")
            
            try:
                # 执行迁移脚本
                for script in migration['scripts']:
                    conn.executescript(script)
                
                # 记录版本信息
                conn.execute(
                    "INSERT INTO db_version (version, description, applied_at) VALUES (?, ?, ?)",
                    (version, description, datetime.utcnow())
                )
                
                # 提交事务
                conn.commit()
                logger.info(f"成功迁移到版本 {version}")
                
            except Exception as e:
                # 回滚事务
                conn.rollback()
                logger.error(f"迁移到版本 {version} 失败: {str(e)}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"执行数据库迁移过程中发生错误: {str(e)}")
        return False

def reset_database():
    """重置数据库（危险操作）"""
    if os.environ.get('FLASK_ENV') == 'production':
        logger.error("生产环境禁止重置数据库")
        return False
    
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # 开始事务
        conn.execute("BEGIN TRANSACTION")
        
        try:
            # 删除外键约束
            conn.execute("PRAGMA foreign_keys = OFF")
            
            # 删除所有表
            for table in tables:
                table_name = table[0]
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # 恢复外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 提交事务
            conn.commit()
            logger.info("数据库已重置")
            
            # 重新运行迁移
            return run_migrations()
            
        except Exception as e:
            # 回滚事务
            conn.rollback()
            logger.error(f"重置数据库失败: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"重置数据库过程中发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 处理命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        if input("确认重置数据库? 所有数据将被删除! (y/n): ").lower() == 'y':
            if reset_database():
                print("数据库重置成功")
            else:
                print("数据库重置失败")
                sys.exit(1)
    else:
        if run_migrations():
            print("数据库迁移成功")
        else:
            print("数据库迁移失败")
            sys.exit(1) 