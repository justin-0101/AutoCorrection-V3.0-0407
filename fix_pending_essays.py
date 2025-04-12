#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接通过SQL删除无效的待处理作文
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

def fix_pending_essays():
    """直接通过SQL删除或修复无效的待处理作文"""
    
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
        
        # 1. 检查待处理作文
        logger.info("检查待处理作文...")
        cursor.execute("SELECT COUNT(*) FROM essays WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]
        logger.info(f"共有 {pending_count} 篇待处理作文")
        
        # 2. 获取所有待处理作文的ID和其他关键信息
        cursor.execute("""
            SELECT id, title, content, user_id, created_at 
            FROM essays 
            WHERE status = 'pending'
        """)
        pending_essays = cursor.fetchall()
        
        # 3. 检查每篇作文的关键字段
        corrupt_ids = []
        for essay in pending_essays:
            essay_id, title, content, user_id, created_at = essay
            
            if not all([essay_id, title, content, user_id]):
                logger.warning(f"发现无效作文 ID: {essay_id}, 标题: {title}, 用户ID: {user_id}")
                corrupt_ids.append(essay_id)
        
        logger.info(f"发现 {len(corrupt_ids)} 篇无效作文")
        
        # 4. 删除所有关联的批改记录
        if corrupt_ids:
            corrupt_ids_str = ','.join(['?' for _ in corrupt_ids])
            cursor.execute(f"""
                DELETE FROM corrections 
                WHERE essay_id IN ({corrupt_ids_str})
            """, corrupt_ids)
            
            deleted_corrections = cursor.rowcount
            logger.info(f"删除了 {deleted_corrections} 条关联的批改记录")
            
            # 5. 将这些作文标记为失败状态
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_message = "作文数据不完整，已被系统标记为失败"
            
            cursor.execute(f"""
                UPDATE essays 
                SET status = 'failed', 
                    error_message = ?, 
                    updated_at = ? 
                WHERE id IN ({corrupt_ids_str})
            """, [error_message, current_time] + corrupt_ids)
            
            updated_essays = cursor.rowcount
            logger.info(f"更新了 {updated_essays} 篇作文状态为失败")
        
        # 6. 检查是否有正在处理但实际未处理的作文
        cursor.execute("""
            SELECT id FROM essays 
            WHERE status IN ('processing', 'correcting') 
            AND updated_at < datetime('now', '-30 minutes')
        """)
        
        stuck_essays = cursor.fetchall()
        stuck_ids = [essay[0] for essay in stuck_essays]
        
        if stuck_ids:
            logger.info(f"发现 {len(stuck_ids)} 篇卡住的作文")
            
            # 重置这些作文的状态
            stuck_ids_str = ','.join(['?' for _ in stuck_ids])
            cursor.execute(f"""
                UPDATE essays 
                SET status = 'pending',
                    updated_at = ? 
                WHERE id IN ({stuck_ids_str})
            """, [current_time] + stuck_ids)
            
            updated_stuck = cursor.rowcount
            logger.info(f"重置了 {updated_stuck} 篇卡住的作文状态为待处理")
            
            # 删除卡住的批改记录
            cursor.execute(f"""
                DELETE FROM corrections 
                WHERE essay_id IN ({stuck_ids_str})
                AND status IN ('processing', 'correcting')
            """, stuck_ids)
            
            deleted_stuck_corrections = cursor.rowcount
            logger.info(f"删除了 {deleted_stuck_corrections} 条卡住的批改记录")
        
        # 7. 提交更改
        conn.commit()
        
        # 8. 验证更改
        cursor.execute("SELECT COUNT(*) FROM essays WHERE status = 'pending'")
        new_pending_count = cursor.fetchone()[0]
        logger.info(f"修复后有 {new_pending_count} 篇待处理作文")
        
        cursor.execute("SELECT COUNT(*) FROM essays WHERE status = 'failed'")
        failed_count = cursor.fetchone()[0]
        logger.info(f"失败状态的作文共 {failed_count} 篇")
        
        # 关闭连接
        conn.close()
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
    logger.info("开始修复无效的待处理作文...")
    
    success = fix_pending_essays()
    
    if success:
        logger.info("修复完成")
    else:
        logger.error("修复失败")
        sys.exit(1) 