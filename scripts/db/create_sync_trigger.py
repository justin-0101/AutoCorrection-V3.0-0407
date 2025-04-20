#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建数据库触发器，用于确保corrections和essays表状态同步
当corrections表中的记录状态更新时，自动更新对应的essay记录状态
"""

import os
import sqlite3
import logging
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_path():
    """获取数据库路径"""
    # 首先尝试当前目录下的instance文件夹
    db_path = "instance/essay_correction.db"
    if os.path.exists(db_path):
        return db_path
    
    # 尝试以脚本所在目录为基准
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))  # 项目根目录
    db_path = os.path.join(root_dir, "instance", "essay_correction.db")
    
    if os.path.exists(db_path):
        return db_path
    
    raise FileNotFoundError(f"数据库文件未找到: {db_path}")

def create_sync_trigger(conn):
    """创建同步触发器"""
    cursor = conn.cursor()
    
    # 检查触发器是否已存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='update_essay_after_correction'")
    if cursor.fetchone():
        logger.info("触发器 'update_essay_after_correction' 已存在，跳过创建")
        return False
    
    # 创建触发器，在corrections表更新后同步更新essays表
    trigger_sql = """
    CREATE TRIGGER update_essay_after_correction
    AFTER UPDATE ON corrections
    FOR EACH ROW
    WHEN (NEW.status <> OLD.status OR NEW.is_deleted <> OLD.is_deleted)
    BEGIN
        UPDATE essays
        SET status = CASE 
                      WHEN NEW.status = 'completed' THEN 'completed'
                      WHEN NEW.status = 'failed' THEN 'failed'
                      WHEN NEW.status = 'correcting' THEN 'correcting'
                      WHEN NEW.status = 'pending' THEN 'pending'
                      ELSE essays.status
                    END,
            error_message = CASE 
                             WHEN NEW.status = 'failed' THEN NEW.error_message
                             ELSE essays.error_message
                           END,
            updated_at = datetime('now')
        WHERE id = NEW.essay_id;
    END;
    """
    
    cursor.execute(trigger_sql)
    conn.commit()
    logger.info("成功创建触发器 'update_essay_after_correction'")
    return True

def create_unique_index(conn):
    """创建唯一索引，确保每篇文章只有一个活跃的'completed'状态批改记录"""
    cursor = conn.cursor()
    
    # 检查索引是否已存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_corrections_active_completed'")
    if cursor.fetchone():
        logger.info("索引 'idx_corrections_active_completed' 已存在，跳过创建")
        return False
    
    # 首先修复可能存在的数据问题
    fix_duplicate_completed_corrections(conn)
    
    # 创建唯一索引
    index_sql = """
    CREATE UNIQUE INDEX idx_corrections_active_completed
    ON corrections (essay_id)
    WHERE status = 'completed' AND is_deleted = 0;
    """
    
    try:
        cursor.execute(index_sql)
        conn.commit()
        logger.info("成功创建唯一索引 'idx_corrections_active_completed'")
        return True
    except sqlite3.OperationalError as e:
        # 如果索引创建失败，可能是因为仍有重复数据
        logger.error(f"创建索引失败: {str(e)}")
        logger.info("尝试再次修复重复数据...")
        conn.rollback()
        fix_duplicate_completed_corrections(conn, aggressive=True)
        
        # 再次尝试创建索引
        try:
            cursor.execute(index_sql)
            conn.commit()
            logger.info("成功创建唯一索引 'idx_corrections_active_completed'")
            return True
        except sqlite3.OperationalError as e:
            logger.error(f"再次尝试创建索引失败: {str(e)}")
            return False

def fix_duplicate_completed_corrections(conn, aggressive=False):
    """修复同一essay_id有多个completed状态的correction记录"""
    cursor = conn.cursor()
    
    # 查找有多个completed状态的essay_id
    query = """
    SELECT essay_id, COUNT(*) AS count
    FROM corrections
    WHERE status = 'completed' AND is_deleted = 0
    GROUP BY essay_id
    HAVING COUNT(*) > 1
    """
    
    cursor.execute(query)
    duplicates = cursor.fetchall()
    
    if not duplicates:
        logger.info("未发现重复的completed状态批改记录")
        return
    
    logger.info(f"发现 {len(duplicates)} 个essay存在多个completed状态的批改记录")
    
    # 处理每个有重复记录的essay
    for essay_id, count in duplicates:
        # 查找该essay的所有completed状态批改记录，按id降序排序
        cursor.execute("""
            SELECT id, created_at, updated_at
            FROM corrections
            WHERE essay_id = ? AND status = 'completed' AND is_deleted = 0
            ORDER BY id DESC
        """, (essay_id,))
        
        records = cursor.fetchall()
        logger.info(f"Essay ID {essay_id} 有 {len(records)} 个completed状态批改记录")
        
        # 保留最新的一条记录，将其他记录标记为is_deleted=1
        keep_id = records[0][0]
        for record_id, created_at, updated_at in records[1:]:
            logger.info(f"将批改记录 ID={record_id} (essay_id={essay_id}) 标记为已删除")
            cursor.execute("""
                UPDATE corrections
                SET is_deleted = 1, status = 'completed', updated_at = datetime('now')
                WHERE id = ?
            """, (record_id,))
    
    # 如果是aggressive模式，还处理pending和其他状态的记录
    if aggressive:
        logger.info("启用激进修复模式，处理所有状态的重复记录")
        cursor.execute("""
            SELECT id, essay_id, status
            FROM corrections 
            WHERE is_deleted = 0
        """)
        
        all_records = {}
        for record_id, essay_id, status in cursor.fetchall():
            if essay_id not in all_records:
                all_records[essay_id] = []
            all_records[essay_id].append((record_id, status))
        
        for essay_id, records in all_records.items():
            if len(records) <= 1:
                continue
                
            # 如果有completed状态的记录，保留它，否则保留ID最大的记录
            has_completed = any(status == 'completed' for _, status in records)
            
            if has_completed:
                # 找到completed状态的记录中ID最大的
                completed_records = [(rid, st) for rid, st in records if st == 'completed']
                keep_id = max(rid for rid, _ in completed_records)
            else:
                # 保留ID最大的记录
                keep_id = max(rid for rid, _ in records)
            
            # 将其他记录标记为已删除
            for record_id, _ in records:
                if record_id != keep_id:
                    logger.info(f"激进模式: 将批改记录 ID={record_id} (essay_id={essay_id}) 标记为已删除")
                    cursor.execute("""
                        UPDATE corrections
                        SET is_deleted = 1, updated_at = datetime('now')
                        WHERE id = ?
                    """, (record_id,))
    
    conn.commit()
    logger.info("成功修复重复的批改记录")

def main():
    """主函数"""
    try:
        db_path = get_db_path()
        logger.info(f"使用数据库路径: {db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # 创建触发器
        trigger_created = create_sync_trigger(conn)
        
        # 创建唯一索引
        index_created = create_unique_index(conn)
        
        if trigger_created or index_created:
            logger.info("数据库结构更新成功")
        else:
            logger.info("数据库结构已是最新，无需更新")
        
        # 关闭连接
        conn.close()
        
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 