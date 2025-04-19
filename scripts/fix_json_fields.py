#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复数据库中的无效JSON字段
将null值或格式不正确的JSON字段替换为有效的空JSON对象
"""

import os
import sys
import logging
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("db_fix_json.log", encoding="utf-8")
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

def fix_json_fields(db_path):
    """修复essays表中的无效JSON字段"""
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取essays表的所有列名
        cursor.execute("PRAGMA table_info(essays)")
        columns = cursor.fetchall()
        json_columns = []
        
        # 检查哪些列可能存储JSON数据
        for col in columns:
            col_name = col[1]
            if col_name in ['error_analysis', 'improvement_suggestions', 'meta_data', 'results']:
                json_columns.append(col_name)
        
        logger.info(f"检测到可能的JSON列: {json_columns}")
        
        # 获取所有essays记录
        cursor.execute("SELECT id FROM essays")
        essays = cursor.fetchall()
        
        fixed_count = 0
        total_count = len(essays)
        logger.info(f"找到 {total_count} 条essays记录")
        
        # 遍历每条记录，检查并修复JSON字段
        for essay in essays:
            essay_id = essay[0]
            
            for col_name in json_columns:
                # 获取当前字段值
                cursor.execute(f"SELECT {col_name} FROM essays WHERE id = ?", (essay_id,))
                result = cursor.fetchone()
                if result is None:
                    continue
                    
                value = result[0]
                
                # 检查JSON是否有效
                if value is None or value == '':
                    # 空值，替换为空JSON对象
                    cursor.execute(f"UPDATE essays SET {col_name} = ? WHERE id = ?", ('{}', essay_id))
                    fixed_count += 1
                    logger.info(f"修复essay_id={essay_id}的{col_name}字段: None -> '{{}}'")
                else:
                    try:
                        # 尝试解析JSON
                        json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        # JSON解析失败，替换为空JSON对象
                        cursor.execute(f"UPDATE essays SET {col_name} = ? WHERE id = ?", ('{}', essay_id))
                        fixed_count += 1
                        logger.info(f"修复essay_id={essay_id}的{col_name}字段: 无效JSON -> '{{}}'")
        
        # 提交更改
        conn.commit()
        logger.info(f"修复完成，共处理{total_count}条记录，修复{fixed_count}个无效JSON字段")
        
        # 现在修复corrections表中的JSON字段
        cursor.execute("PRAGMA table_info(corrections)")
        columns = cursor.fetchall()
        json_columns = []
        
        # 检查哪些列可能存储JSON数据
        for col in columns:
            col_name = col[1]
            if col_name in ['error_analysis', 'extra_data', 'results']:
                json_columns.append(col_name)
        
        logger.info(f"检测到corrections表中可能的JSON列: {json_columns}")
        
        # 获取所有corrections记录
        cursor.execute("SELECT id FROM corrections")
        corrections = cursor.fetchall()
        
        fixed_count = 0
        total_count = len(corrections)
        logger.info(f"找到 {total_count} 条corrections记录")
        
        # 遍历每条记录，检查并修复JSON字段
        for correction in corrections:
            correction_id = correction[0]
            
            for col_name in json_columns:
                # 获取当前字段值
                cursor.execute(f"SELECT {col_name} FROM corrections WHERE id = ?", (correction_id,))
                result = cursor.fetchone()
                if result is None:
                    continue
                    
                value = result[0]
                
                # 检查JSON是否有效
                if value is None or value == '':
                    # 空值，替换为空JSON对象
                    cursor.execute(f"UPDATE corrections SET {col_name} = ? WHERE id = ?", ('{}', correction_id))
                    fixed_count += 1
                    logger.info(f"修复correction_id={correction_id}的{col_name}字段: None -> '{{}}'")
                else:
                    try:
                        # 尝试解析JSON
                        json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        # JSON解析失败，替换为空JSON对象
                        cursor.execute(f"UPDATE corrections SET {col_name} = ? WHERE id = ?", ('{}', correction_id))
                        fixed_count += 1
                        logger.info(f"修复correction_id={correction_id}的{col_name}字段: 无效JSON -> '{{}}'")
        
        # 提交更改
        conn.commit()
        logger.info(f"修复corrections表完成，共处理{total_count}条记录，修复{fixed_count}个无效JSON字段")
        
        return True
    
    except sqlite3.Error as e:
        logger.error(f"SQLite错误: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        logger.error(f"未预期的错误: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def main():
    """主函数"""
    print("===== 数据库JSON字段修复工具 =====")
    
    # 获取数据库路径
    db_path = get_db_path()
    
    # 修复JSON字段
    success = fix_json_fields(db_path)
    
    if success:
        print("✅ 修复成功完成！请重新启动应用以验证问题是否解决。")
    else:
        print("❌ 修复失败，请查看日志了解详细信息。")

if __name__ == "__main__":
    main() 