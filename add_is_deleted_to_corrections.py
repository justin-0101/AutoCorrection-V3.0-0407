#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向corrections表添加is_deleted字段的迁移脚本
"""

import os
import sys
import logging
import sqlite3
import traceback

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def add_is_deleted_column():
    """向corrections表添加is_deleted字段"""
    
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
        
        # 1. 检查corrections表结构
        logger.info("检查corrections表结构...")
        cursor.execute("PRAGMA table_info(corrections)")
        columns = cursor.fetchall()
        
        # 检查是否已存在is_deleted字段
        has_is_deleted = any(column[1] == 'is_deleted' for column in columns)
        
        if has_is_deleted:
            logger.info("corrections表已经有is_deleted字段，无需添加")
            return True
        
        # 2. 添加is_deleted字段
        logger.info("添加is_deleted字段...")
        cursor.execute("ALTER TABLE corrections ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0")
        conn.commit()
        
        # 3. 验证字段添加结果
        cursor.execute("PRAGMA table_info(corrections)")
        columns = cursor.fetchall()
        has_is_deleted = any(column[1] == 'is_deleted' for column in columns)
        
        if has_is_deleted:
            logger.info("is_deleted字段已成功添加到corrections表")
            return True
        else:
            logger.error("添加字段后验证失败，is_deleted字段未找到")
            return False
        
    except Exception as e:
        logger.error(f"添加is_deleted字段时发生错误: {str(e)}\n{traceback.format_exc()}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    """主函数"""
    try:
        logger.info("开始执行迁移...")
        
        # 添加is_deleted字段
        if add_is_deleted_column():
            logger.info("迁移成功完成")
            return 0
        else:
            logger.error("迁移失败")
            return 1
            
    except Exception as e:
        logger.error(f"执行迁移时发生未处理的错误: {str(e)}\n{traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 