#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库迁移脚本：为corrections表添加唯一索引
确保每篇文章只有一条未删除且状态为completed的批改记录
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("db_migration.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# 确保运行路径是项目根目录
project_root = Path(__file__).resolve().parent.parent
os.chdir(project_root)

def get_db_path():
    """获取数据库路径"""
    # 默认使用标准路径
    db_path = os.path.join(project_root, 'instance', 'essay_correction.db')
    
    # 尝试从.env文件获取数据库路径
    env_path = os.path.join(project_root, '.env')
    
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('DATABASE_URI='):
                        db_uri = line.strip().split('=', 1)[1].strip('"\'')
                        if db_uri.startswith('sqlite:///'):
                            custom_path = db_uri[10:]
                            if os.path.exists(custom_path):
                                db_path = custom_path
                        break
        except Exception as e:
            logger.warning(f"读取.env文件出错: {e}，使用默认数据库路径")
    
    logger.info(f"使用数据库路径: {db_path}")
    return db_path

def create_unique_index(db_path):
    """为corrections表创建唯一索引"""
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 设置外键约束
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 检查索引是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_corrections_active_completed'")
        if cursor.fetchone():
            logger.info("索引'idx_corrections_active_completed'已存在，无需创建")
            return True
        
        # 创建保证唯一性的索引
        logger.info("创建唯一索引...")
        cursor.execute("""
            CREATE UNIQUE INDEX idx_corrections_active_completed 
            ON corrections (essay_id) 
            WHERE is_deleted = 0 AND status = 'completed'
        """)
        
        # 验证索引创建成功
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_corrections_active_completed'")
        if cursor.fetchone():
            logger.info("唯一索引创建成功!")
            conn.commit()
            return True
        else:
            logger.error("创建索引失败")
            return False
    
    except sqlite3.Error as e:
        logger.error(f"SQLite错误: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def main():
    """主函数"""
    print("===== 数据库迁移：添加唯一索引 =====")
    
    # 获取数据库路径
    db_path = get_db_path()
    
    # 创建唯一索引
    success = create_unique_index(db_path)
    
    if success:
        print("✅ 迁移成功完成！现在每篇文章只能有一条未删除且状态为completed的批改记录")
    else:
        print("❌ 迁移失败，请查看日志了解详细信息")

if __name__ == "__main__":
    main() 