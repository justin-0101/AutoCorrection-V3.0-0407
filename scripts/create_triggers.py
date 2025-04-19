#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建SQLite触发器，确保corrections表和essays表的数据一致性
当corrections表记录更新为completed状态时，自动更新相应的essay记录
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
        logging.FileHandler("db_triggers.log", encoding="utf-8")
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

def create_triggers(db_path):
    """创建数据库触发器"""
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 设置外键约束
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 检查触发器是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='update_essay_after_correction'")
        if cursor.fetchone():
            logger.info("触发器'update_essay_after_correction'已存在，删除旧触发器")
            cursor.execute("DROP TRIGGER IF EXISTS update_essay_after_correction")
        
        # 创建触发器：当corrections表的记录更新为completed状态时，更新对应的essay记录
        logger.info("创建触发器'update_essay_after_correction'...")
        
        # 注意：SQLite触发器不支持UPDATE OF特定字段，只能是整个表的UPDATE
        trigger_sql = """
        CREATE TRIGGER update_essay_after_correction
        AFTER UPDATE ON corrections
        FOR EACH ROW
        WHEN NEW.status = 'completed' AND OLD.status != 'completed' AND NEW.is_deleted = 0
        BEGIN
            UPDATE essays
            SET score = NEW.score,
                comments = NEW.comments,
                error_analysis = NEW.error_analysis,
                improvement_suggestions = NEW.improvement_suggestions,
                status = 'completed',
                updated_at = NEW.updated_at
            WHERE id = NEW.essay_id;
        END;
        """
        cursor.execute(trigger_sql)
        
        # 验证触发器创建成功
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='update_essay_after_correction'")
        if cursor.fetchone():
            logger.info("触发器创建成功!")
            conn.commit()
            return True
        else:
            logger.error("创建触发器失败")
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
    print("===== 创建数据库触发器 =====")
    
    # 获取数据库路径
    db_path = get_db_path()
    
    # 创建触发器
    success = create_triggers(db_path)
    
    if success:
        print("✅ 触发器创建成功！现在当批改记录更新为completed状态时，系统将自动更新对应的作文记录")
    else:
        print("❌ 触发器创建失败，请查看日志了解详细信息")

if __name__ == "__main__":
    main() 