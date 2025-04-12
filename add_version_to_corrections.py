#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向corrections表添加version字段的迁移脚本
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

def add_version_column():
    """向corrections表添加version字段"""
    
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
        column_names = [col[1] for col in columns]
        
        # 2. 检查version列是否存在
        if 'version' in column_names:
            logger.info("version列已存在，无需添加")
            conn.close()
            return True
        
        logger.info("准备添加version列...")
        
        # 3. 添加版本列
        try:
            cursor.execute("ALTER TABLE corrections ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
            conn.commit()
            logger.info("成功添加version列")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.warning("version列已存在，跳过添加")
            else:
                logger.error(f"添加version列时出错: {str(e)}")
                conn.rollback()
                conn.close()
                return False
        
        # 4. 验证添加结果
        cursor.execute("PRAGMA table_info(corrections)")
        columns_after = cursor.fetchall()
        column_names_after = [col[1] for col in columns_after]
        
        if 'version' in column_names_after:
            logger.info("验证成功：version列已存在")
        else:
            logger.error("验证失败：version列添加失败")
            conn.close()
            return False
        
        # 5. 添加essays表的version列
        logger.info("检查essays表是否需要添加version列...")
        cursor.execute("PRAGMA table_info(essays)")
        essays_columns = cursor.fetchall()
        essays_column_names = [col[1] for col in essays_columns]
        
        if 'version' not in essays_column_names:
            try:
                logger.info("添加essays表的version列...")
                cursor.execute("ALTER TABLE essays ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
                conn.commit()
                logger.info("成功添加essays表的version列")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logger.warning("essays表的version列已存在，跳过添加")
                else:
                    logger.error(f"添加essays表的version列时出错: {str(e)}")
        else:
            logger.info("essays表的version列已存在，无需添加")
        
        # 关闭连接
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"添加version列时出错: {str(e)}")
        logger.error(traceback.format_exc())
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

if __name__ == "__main__":
    logger.info("开始向corrections表添加version字段...")
    
    success = add_version_column()
    
    if success:
        logger.info("迁移完成")
    else:
        logger.error("迁移失败")
        sys.exit(1) 