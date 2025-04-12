#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查essays表的结构，验证version字段是否已添加
"""

import os
import sqlite3
import logging
from pathlib import Path

# 设置日志 - 添加控制台输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 添加控制台处理器
    ]
)
logger = logging.getLogger(__name__)

def get_sqlite_path():
    """获取SQLite数据库路径"""
    # 项目根目录
    base_dir = Path(__file__).resolve().parent
    
    # 数据库文件路径（在instance目录下）
    db_path = os.path.join(base_dir, 'instance', 'essay_correction.db')
    
    print(f"数据库路径: {db_path}")
    logger.info(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"警告: 数据库文件不存在 {db_path}")
        logger.warning(f"警告: 数据库文件不存在 {db_path}")
        
    return db_path

def check_essays_table():
    """检查essays表的结构"""
    try:
        # 连接数据库
        db_path = get_sqlite_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='essays'")
        if not cursor.fetchone():
            print("essays表不存在")
            logger.error("essays表不存在")
            return
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(essays)")
        columns = cursor.fetchall()
        
        # 打印表结构
        print("===== essays表结构 =====")
        logger.info("===== essays表结构 =====")
        for col in columns:
            col_info = f"列名: {col['name']}, 类型: {col['type']}, 可空: {col['notnull'] == 0}, 默认值: {col['dflt_value']}"
            print(col_info)
            logger.info(col_info)
        
        # 特别检查version字段
        version_col = next((col for col in columns if col['name'] == 'version'), None)
        if version_col:
            version_info = f"✅ version字段已存在: 类型={version_col['type']}, 默认值={version_col['dflt_value']}"
            print(version_info)
            logger.info(version_info)
        else:
            print("❌ version字段不存在")
            logger.error("❌ version字段不存在")
        
        # 检查索引
        cursor.execute("PRAGMA index_list(essays)")
        indexes = cursor.fetchall()
        
        print("===== essays表索引 =====")
        logger.info("===== essays表索引 =====")
        for idx in indexes:
            idx_info = f"索引名: {idx['name']}, 唯一: {idx['unique']}"
            print(idx_info)
            logger.info(idx_info)
            
            # 获取索引的列
            cursor.execute(f"PRAGMA index_info({idx['name']})")
            index_columns = cursor.fetchall()
            columns_str = ", ".join(f"{col['name']}" for col in index_columns)
            print(f"  - 包含列: {columns_str}")
            logger.info(f"  - 包含列: {columns_str}")
            
        # 检查version索引
        version_index = next((idx for idx in indexes if idx['name'] == 'ix_essays_version'), None)
        if version_index:
            print("✅ version字段索引已存在")
            logger.info("✅ version字段索引已存在")
        else:
            print("❌ version字段索引不存在")
            logger.error("❌ version字段索引不存在")
            
    except Exception as e:
        error_msg = f"检查表结构时出错: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("开始检查essays表结构...")
    check_essays_table()
    print("检查完成。") 