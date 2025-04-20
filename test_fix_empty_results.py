#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试修复空批改结果脚本
独立运行，不依赖Flask应用上下文
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

DB_PATH = "instance/essay_correction.db"

def connect_db():
    """连接数据库"""
    if not os.path.exists(DB_PATH):
        logger.error(f"错误: 数据库文件 {DB_PATH} 不存在!")
        return None
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 设置行工厂，使结果可以通过列名访问
        logger.info(f"成功连接到数据库: {DB_PATH}")
        return conn
    except Exception as e:
        logger.error(f"连接数据库出错: {e}")
        return None

def check_empty_results(conn, days_ago=7):
    """检查最近N天内批改结果为空或无效的记录"""
    logger.info(f"开始查找最近{days_ago}天内批改结果为空或无效的记录")
    cutoff_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    cursor = conn.cursor()
    empty_results = []
    
    try:
        # 查找状态为completed但results为空或无效的记录
        cursor.execute("""
            SELECT c.id, c.essay_id, c.score, c.results, c.status,
                   e.title, e.status as essay_status
            FROM corrections c
            JOIN essays e ON c.essay_id = e.id
            WHERE c.status = 'completed' 
              AND e.status = 'completed'
              AND c.is_deleted = 0
              AND e.created_at >= ?
        """, (cutoff_date,))
        
        records = cursor.fetchall()
        logger.info(f"找到最近{days_ago}天内的{len(records)}条已完成批改记录")
        
        for record in records:
            correction_id = record['id']
            essay_id = record['essay_id']
            title = record['title']
            results = record['results']
            
            needs_fix = False
            reason = ""
            
            # 检查results是否为空
            if not results:
                reason = "批改结果为空"
                needs_fix = True
            else:
                # 检查results是否为有效JSON
                try:
                    results_json = json.loads(results)
                    logger.info(f"correction_id={correction_id} (essay_id={essay_id}) JSON结构: {list(results_json.keys())}")
                    
                    # 检查results是否完整（至少包含总得分和分项得分）
                    has_total_score = '总得分' in results_json or 'total_score' in results_json
                    has_detailed_scores = '分项得分' in results_json or ('content_score' in results_json and 'language_score' in results_json)
                    
                    if not (has_total_score and has_detailed_scores):
                        logger.warning(f"批改结果缺少必要字段 - 总分: {has_total_score}, 分项分数: {has_detailed_scores}")
                        reason = "批改结果数据不完整"
                        needs_fix = True
                except json.JSONDecodeError:
                    reason = "批改结果JSON无效"
                    needs_fix = True
            
            if needs_fix:
                logger.warning(f"correction_id={correction_id} (essay_id={essay_id}, '{title}') {reason}")
                empty_results.append({
                    'correction_id': correction_id,
                    'essay_id': essay_id,
                    'title': title,
                    'reason': reason
                })
        
        logger.info(f"发现{len(empty_results)}条需要修复的记录")
        for i, record in enumerate(empty_results, 1):
            logger.info(f"{i}. essay_id={record['essay_id']} ({record['title']}) - {record['reason']}")
        
        return empty_results
        
    except sqlite3.Error as e:
        logger.error(f"查询数据库错误: {e}")
        return []

def main():
    """主函数"""
    logger.info("===== 空批改结果检查工具 =====")
    
    # 连接数据库
    conn = connect_db()
    if not conn:
        logger.error("无法连接数据库，退出程序。")
        return 1
    
    try:
        # 获取命令行参数
        days = 7
        if len(sys.argv) > 1:
            try:
                days = int(sys.argv[1])
            except ValueError:
                logger.warning(f"无效的天数参数: {sys.argv[1]}，使用默认值: 7")
        
        # 检查空批改结果
        empty_results = check_empty_results(conn, days)
        
        if not empty_results:
            logger.info(f"未发现最近{days}天内需要修复的记录")
            return 0
        
        logger.info(f"发现{len(empty_results)}条记录需要修复，请使用fix_correction_results.py修复")
        for record in empty_results:
            logger.info(f"可运行: python fix_correction_results.py {record['essay_id']}")
        
        return 0
    
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        traceback.print_exc()
        return 1
    
    finally:
        if conn:
            conn.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    sys.exit(main()) 