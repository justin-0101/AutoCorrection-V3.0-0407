#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库迁移脚本，添加唯一索引到corrections表
确保每篇文章只能有一条未删除的记录
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
        except UnicodeDecodeError:
            logger.warning("无法以UTF-8编码读取.env文件，使用默认数据库路径")
    
    logger.info(f"使用数据库路径: {db_path}")
    return db_path

def add_unique_index(db_path):
    """添加唯一索引到corrections表"""
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查index是否已经存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uix_corrections_essay_active'")
        existing_index = cursor.fetchone()
        
        if existing_index:
            logger.info("索引'uix_corrections_essay_active'已存在，无需创建")
            return True
        
        # 检查是否有重复记录
        cursor.execute("""
            SELECT essay_id, COUNT(*) as count 
            FROM corrections 
            WHERE is_deleted = 0
            GROUP BY essay_id 
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            logger.warning(f"发现{len(duplicates)}个essay_id有多条未删除的correction记录")
            logger.warning("请先运行fix_duplicate_corrections.py脚本修复重复记录")
            
            for essay_id, count in duplicates:
                logger.warning(f"essay_id={essay_id} 有 {count} 条未删除的记录")
            
            # 自动修复重复记录
            logger.info("尝试自动修复重复记录...")
            
            for essay_id, _ in duplicates:
                # 获取所有记录
                cursor.execute("""
                    SELECT id, updated_at FROM corrections 
                    WHERE essay_id = ? AND is_deleted = 0
                    ORDER BY updated_at DESC
                """, (essay_id,))
                records = cursor.fetchall()
                
                # 保留最新的记录，标记其他记录为已删除
                latest_id = records[0][0]
                other_ids = [r[0] for r in records[1:]]
                
                if other_ids:
                    cursor.execute("""
                        UPDATE corrections 
                        SET is_deleted = 1
                        WHERE id IN ({})
                    """.format(','.join(['?'] * len(other_ids))), other_ids)
                    
                    logger.info(f"已将essay_id={essay_id}的{len(other_ids)}条记录标记为已删除，保留ID={latest_id}的记录")
            
            conn.commit()
        
        # 创建唯一索引
        logger.info("创建唯一索引'uix_corrections_essay_active'...")
        cursor.execute("""
            CREATE UNIQUE INDEX uix_corrections_essay_active
            ON corrections (essay_id) 
            WHERE is_deleted = 0
        """)
        
        # 验证索引是否创建成功
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uix_corrections_essay_active'")
        index = cursor.fetchone()
        
        if index:
            logger.info("唯一索引'uix_corrections_essay_active'创建成功")
            conn.commit()
            return True
        else:
            logger.error("唯一索引创建失败")
            return False
        
    except sqlite3.Error as e:
        logger.error(f"SQLite错误: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    logger.info("===== 数据库迁移：添加唯一索引 =====")
    
    # 获取数据库路径
    db_path = get_db_path()
    
    # 添加唯一索引
    result = add_unique_index(db_path)
    
    if result:
        logger.info("迁移成功完成！现在每篇文章只能有一条未删除的correction记录")
    else:
        logger.error("迁移失败")

if __name__ == "__main__":
    main() 