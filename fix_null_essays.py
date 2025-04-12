#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接删除ID为NULL的无效作文记录
解决'NoneType' object has no attribute 'id'错误
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def fix_null_essays():
    """直接删除ID为NULL的无效作文记录"""
    
    # 确定数据库路径
    db_path = os.path.join('instance', 'essay_correction.db')
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    logger.info(f"连接数据库: {db_path}")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 启用外键支持
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 1. 检查所有作文记录
        logger.info("检查所有作文记录...")
        cursor.execute("SELECT COUNT(*) FROM essays")
        total_count = cursor.fetchone()[0]
        logger.info(f"共有 {total_count} 篇作文")
        
        # 2. 检查并输出一些问题作文的信息（ID为NULL或内容异常）
        cursor.execute("""
            SELECT id, title, content, user_id, status, created_at
            FROM essays 
            WHERE id IS NULL OR title IS NULL OR content IS NULL OR user_id IS NULL
        """)
        invalid_essays = cursor.fetchall()
        
        for essay in invalid_essays:
            essay_id, title, content, user_id, status, created_at = essay
            logger.warning(f"发现无效作文 - ID: {essay_id}, 标题: {title}, 用户ID: {user_id}, 状态: {status}")
        
        logger.info(f"发现 {len(invalid_essays)} 篇无效作文记录")
        
        # 3. 创建一个临时表保存有效记录
        logger.info("创建临时表...")
        cursor.execute("DROP TABLE IF EXISTS essays_temp")
        cursor.execute("""
            CREATE TABLE essays_temp AS 
            SELECT * FROM essays 
            WHERE id IS NOT NULL AND title IS NOT NULL AND content IS NOT NULL AND user_id IS NOT NULL
        """)
        
        cursor.execute("SELECT COUNT(*) FROM essays_temp")
        valid_count = cursor.fetchone()[0]
        logger.info(f"临时表中保存了 {valid_count} 篇有效作文记录")
        
        # 4. 删除相关的批改记录
        logger.info("删除无效作文相关的批改记录...")
        cursor.execute("""
            DELETE FROM corrections 
            WHERE essay_id NOT IN (SELECT id FROM essays_temp)
        """)
        deleted_corrections = cursor.rowcount
        logger.info(f"删除了 {deleted_corrections} 条关联的批改记录")
        
        # 5. 备份原表
        logger.info("备份原表...")
        backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        cursor.execute(f"ALTER TABLE essays RENAME TO essays_backup_{backup_time}")
        
        # 6. 将临时表改名为正式表
        logger.info("恢复有效记录...")
        cursor.execute("ALTER TABLE essays_temp RENAME TO essays")
        
        # 7. 重建索引
        logger.info("重建索引...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_essays_user_id ON essays(user_id);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_essays_status ON essays(status);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_essays_created_at ON essays(created_at);
        """)
        
        # 8. 提交更改
        conn.commit()
        
        # 9. 验证更改
        cursor.execute("SELECT COUNT(*) FROM essays")
        new_total = cursor.fetchone()[0]
        logger.info(f"修复后总共有 {new_total} 篇作文记录")
        
        cursor.execute("SELECT COUNT(*) FROM essays WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]
        logger.info(f"修复后有 {pending_count} 篇待处理作文")
        
        # 关闭连接
        conn.close()
        
        # 计算删除的记录数
        cleaned_count = total_count - new_total
        logger.info(f"成功清理了 {cleaned_count} 篇无效作文记录")
        
        return True
        
    except Exception as e:
        logger.error(f"修复过程中出错: {str(e)}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

if __name__ == "__main__":
    logger.info("开始修复ID为NULL的无效作文记录...")
    
    success = fix_null_essays()
    
    if success:
        logger.info("修复完成")
    else:
        logger.error("修复失败")
        sys.exit(1) 