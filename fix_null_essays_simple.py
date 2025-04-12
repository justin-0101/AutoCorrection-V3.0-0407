#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简化版 - 直接删除ID为NULL的无效作文记录
"""

import os
import sys
import logging
import sqlite3

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def fix_null_essays_simple():
    """直接删除ID为NULL的无效作文记录 - 简化版"""
    
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
        
        # 1. 检查所有作文记录
        logger.info("检查所有作文记录...")
        cursor.execute("SELECT COUNT(*) FROM essays")
        total_count = cursor.fetchone()[0]
        logger.info(f"共有 {total_count} 篇作文")
        
        # 2. 检查并输出有问题的记录
        cursor.execute("SELECT COUNT(*) FROM essays WHERE id IS NULL")
        null_id_count = cursor.fetchone()[0]
        logger.info(f"ID为NULL的记录: {null_id_count} 篇")
        
        # 3. 直接删除ID为NULL的记录
        if null_id_count > 0:
            logger.info("删除ID为NULL的记录...")
            cursor.execute("DELETE FROM essays WHERE id IS NULL")
            deleted_count = cursor.rowcount
            logger.info(f"删除了 {deleted_count} 篇ID为NULL的作文记录")
            
            # 4. 查看清理后的结果
            cursor.execute("SELECT COUNT(*) FROM essays")
            after_count = cursor.fetchone()[0]
            logger.info(f"清理后总共有 {after_count} 篇作文记录")
            
            cursor.execute("SELECT COUNT(*) FROM essays WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]
            logger.info(f"清理后有 {pending_count} 篇待处理作文")
            
            # 5. 提交更改
            conn.commit()
            
        else:
            logger.info("没有ID为NULL的记录，无需清理")
        
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
    logger.info("开始简化版修复ID为NULL的无效作文记录...")
    
    success = fix_null_essays_simple()
    
    if success:
        logger.info("修复完成")
    else:
        logger.error("修复失败")
        sys.exit(1) 