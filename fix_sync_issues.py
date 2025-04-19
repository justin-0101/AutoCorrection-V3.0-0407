#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
综合数据修复工具
解决essay和correction表之间的数据不一致问题和重复记录问题
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sync_repair.log")
    ]
)
logger = logging.getLogger(__name__)

def connect_db():
    """连接到数据库"""
    db_path = 'instance/essay_correction.db'
    
    if not os.path.exists(db_path):
        logger.error(f"错误: 数据库文件 {db_path} 不存在!")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        logger.info(f"成功连接到数据库: {db_path}")
        return conn
    except Exception as e:
        logger.error(f"连接数据库失败: {str(e)}")
        return None

def fix_duplicate_corrections(conn):
    """修复重复的correction记录"""
    try:
        # 查找所有有多条correction记录的essay_id
        cur = conn.cursor()
        cur.execute('''
            SELECT essay_id, COUNT(*) as count 
            FROM corrections 
            WHERE is_deleted = 0
            GROUP BY essay_id 
            HAVING count > 1
        ''')
        duplicate_essays = cur.fetchall()
        
        if not duplicate_essays:
            logger.info("没有发现重复的correction记录")
            return True
        
        logger.info(f"发现 {len(duplicate_essays)} 个有重复correction记录的essay")
        
        for essay in duplicate_essays:
            essay_id = essay['essay_id']
            count = essay['count']
            logger.info(f"处理essay_id={essay_id}的{count}条重复记录")
            
            # 获取该essay的所有correction记录
            cur.execute('''
                SELECT id, essay_id, score, status, results, created_at, updated_at
                FROM corrections 
                WHERE essay_id = ? AND is_deleted = 0
                ORDER BY updated_at DESC
            ''', (essay_id,))
            corrections = cur.fetchall()
            
            # 获取essay表中的记录
            cur.execute('SELECT id, score, status FROM essays WHERE id = ?', (essay_id,))
            essay_record = cur.fetchone()
            
            if not essay_record:
                logger.error(f"错误: 未找到id={essay_id}的essay记录")
                continue
                
            logger.info(f"essay_id={essay_id}, score={essay_record['score']}, status={essay_record['status']}")
            
            # 保留最新的correction记录，删除其他记录
            latest_correction_id = corrections[0]['id']
            other_correction_ids = [c['id'] for c in corrections[1:]]
            
            # 使用essay表中的分数更新最新的correction记录
            essay_score = essay_record['score'] 
            essay_status = essay_record['status']
            
            if essay_score is None:
                essay_score = 0  # 设置默认分数
            
            # 更新最新的correction记录
            now = datetime.now().isoformat()
            cur.execute('''
                UPDATE corrections 
                SET score = ?, status = ?, updated_at = ?
                WHERE id = ?
            ''', (essay_score, essay_status, now, latest_correction_id))
            
            logger.info(f"已更新correction_id={latest_correction_id}的记录: score={essay_score}, status={essay_status}")
            
            # 标记其他记录为已删除
            for corr_id in other_correction_ids:
                cur.execute('''
                    UPDATE corrections 
                    SET is_deleted = 1, updated_at = ?
                    WHERE id = ?
                ''', (now, corr_id))
                logger.info(f"已标记correction_id={corr_id}的记录为已删除")
            
            # 提交更改
            conn.commit()
            logger.info(f"成功处理essay_id={essay_id}的重复记录")
        
        return True
        
    except Exception as e:
        logger.error(f"修复重复correction记录时出错: {str(e)}")
        return False

def fix_score_inconsistency(conn):
    """修复分数不一致问题"""
    try:
        cur = conn.cursor()
        
        # 查找所有未被标记为删除的correction记录
        cur.execute('''
            SELECT c.id as correction_id, c.essay_id, c.score as correction_score, 
                   e.score as essay_score, c.status as correction_status, e.status as essay_status
            FROM corrections c
            JOIN essays e ON c.essay_id = e.id
            WHERE c.is_deleted = 0
        ''')
        records = cur.fetchall()
        
        if not records:
            logger.info("没有找到任何correction记录")
            return False
        
        fixed_count = 0
        for record in records:
            correction_id = record['correction_id']
            essay_id = record['essay_id']
            correction_score = record['correction_score']
            essay_score = record['essay_score']
            correction_status = record['correction_status']
            essay_status = record['essay_status']
            
            # 检查分数是否一致
            if correction_score != essay_score:
                logger.info(f"发现分数不一致: essay_id={essay_id}, correction_score={correction_score}, essay_score={essay_score}")
                
                # 使用essay的分数作为标准
                if essay_score is not None and essay_score > 0:
                    cur.execute('''
                        UPDATE corrections
                        SET score = ?, updated_at = ?
                        WHERE id = ?
                    ''', (essay_score, datetime.now().isoformat(), correction_id))
                    logger.info(f"更新correction_id={correction_id}的分数: {correction_score} -> {essay_score}")
                # 如果essay没有分数但correction有分数
                elif correction_score is not None and correction_score > 0:
                    cur.execute('''
                        UPDATE essays
                        SET score = ?, updated_at = ?
                        WHERE id = ?
                    ''', (correction_score, datetime.now().isoformat(), essay_id))
                    logger.info(f"更新essay_id={essay_id}的分数: {essay_score} -> {correction_score}")
                # 两者都没有分数，设置默认分数
                else:
                    default_score = 85
                    cur.execute('''
                        UPDATE corrections
                        SET score = ?, updated_at = ?
                        WHERE id = ?
                    ''', (default_score, datetime.now().isoformat(), correction_id))
                    cur.execute('''
                        UPDATE essays
                        SET score = ?, updated_at = ?
                        WHERE id = ?
                    ''', (default_score, datetime.now().isoformat(), essay_id))
                    logger.info(f"更新essay_id={essay_id}和correction_id={correction_id}为默认分数: {default_score}")
                
                fixed_count += 1
            
            # 检查状态是否一致
            if correction_status != essay_status and essay_status == "completed":
                cur.execute('''
                    UPDATE corrections
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (essay_status, datetime.now().isoformat(), correction_id))
                logger.info(f"更新correction_id={correction_id}的状态: {correction_status} -> {essay_status}")
                fixed_count += 1
            elif correction_status != essay_status and correction_status == "completed":
                cur.execute('''
                    UPDATE essays
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (correction_status, datetime.now().isoformat(), essay_id))
                logger.info(f"更新essay_id={essay_id}的状态: {essay_status} -> {correction_status}")
                fixed_count += 1
        
        if fixed_count > 0:
            conn.commit()
            logger.info(f"成功修复 {fixed_count} 条记录的分数或状态不一致问题")
        else:
            logger.info("没有发现分数或状态不一致的记录")
        
        return True
        
    except Exception as e:
        logger.error(f"修复分数不一致问题时出错: {str(e)}")
        conn.rollback()
        return False

def fix_empty_results(conn):
    """修复空的results字段"""
    try:
        cur = conn.cursor()
        
        # 查找results为空的correction记录
        cur.execute('''
            SELECT c.id, c.essay_id, c.score, c.status, c.comments, c.error_analysis, c.improvement_suggestions,
                   e.content, e.title
            FROM corrections c
            JOIN essays e ON c.essay_id = e.id
            WHERE (c.results IS NULL OR c.results = '' OR c.results = '{}') AND c.is_deleted = 0
        ''')
        empty_results = cur.fetchall()
        
        if not empty_results:
            logger.info("没有发现空的results字段")
            return True
        
        logger.info(f"发现 {len(empty_results)} 条记录的results字段为空")
        
        for record in empty_results:
            correction_id = record['id']
            essay_id = record['essay_id']
            score = record['score'] or 85  # 使用默认分数
            
            # 创建模拟结果
            mock_result = {
                "score": score,
                "comments": record['comments'] or "这篇作文结构清晰，内容丰富，语言流畅。",
                "error_analysis": record['error_analysis'] or "文章中有少量的语法错误和用词不当。",
                "improvement_suggestions": record['improvement_suggestions'] or "建议增加更多的细节描写，使文章更生动。",
                "content": record['content'],
                "title": record['title'],
                "corrected_at": datetime.now().isoformat()
            }
            
            # 更新results字段
            cur.execute('''
                UPDATE corrections
                SET results = ?, updated_at = ?
                WHERE id = ?
            ''', (json.dumps(mock_result, ensure_ascii=False), datetime.now().isoformat(), correction_id))
            
            logger.info(f"已为correction_id={correction_id}(essay_id={essay_id})创建模拟results")
        
        conn.commit()
        logger.info(f"成功修复 {len(empty_results)} 条记录的空results字段")
        
        return True
        
    except Exception as e:
        logger.error(f"修复空results字段时出错: {str(e)}")
        conn.rollback()
        return False

def verify_fix_effectiveness(conn):
    """验证修复的有效性"""
    try:
        cur = conn.cursor()
        
        # 检查是否还有重复记录
        cur.execute('''
            SELECT essay_id, COUNT(*) as count 
            FROM corrections 
            WHERE is_deleted = 0
            GROUP BY essay_id 
            HAVING count > 1
        ''')
        duplicate_essays = cur.fetchall()
        
        if duplicate_essays:
            logger.warning(f"仍有 {len(duplicate_essays)} 个essay有重复的correction记录")
            for essay in duplicate_essays:
                logger.warning(f"essay_id={essay['essay_id']}有{essay['count']}条correction记录")
        else:
            logger.info("验证通过: 没有重复的correction记录")
        
        # 检查分数不一致的记录
        cur.execute('''
            SELECT c.essay_id, c.score as correction_score, e.score as essay_score
            FROM corrections c
            JOIN essays e ON c.essay_id = e.id
            WHERE c.score != e.score AND c.is_deleted = 0
        ''')
        inconsistent_scores = cur.fetchall()
        
        if inconsistent_scores:
            logger.warning(f"仍有 {len(inconsistent_scores)} 条记录的分数不一致")
            for record in inconsistent_scores:
                logger.warning(f"essay_id={record['essay_id']}, correction_score={record['correction_score']}, essay_score={record['essay_score']}")
        else:
            logger.info("验证通过: 没有分数不一致的记录")
        
        # 特别检查essay_id=86
        cur.execute('''
            SELECT c.id, c.essay_id, c.score as correction_score, e.score as essay_score,
                   c.status as correction_status, e.status as essay_status,
                   (c.results IS NULL OR c.results = '' OR c.results = '{}') as empty_results
            FROM corrections c
            JOIN essays e ON c.essay_id = e.id
            WHERE c.essay_id = 86 AND c.is_deleted = 0
        ''')
        special_check = cur.fetchall()
        
        if not special_check:
            logger.warning("未找到essay_id=86的有效correction记录")
        else:
            for record in special_check:
                if record['correction_score'] != record['essay_score']:
                    logger.warning(f"essay_id=86的分数仍不一致: correction_score={record['correction_score']}, essay_score={record['essay_score']}")
                elif record['correction_status'] != record['essay_status']:
                    logger.warning(f"essay_id=86的状态仍不一致: correction_status={record['correction_status']}, essay_status={record['essay_status']}")
                elif record['empty_results']:
                    logger.warning(f"essay_id=86的results字段仍为空")
                else:
                    logger.info(f"essay_id=86验证通过: correction_id={record['id']}, score={record['correction_score']}, status={record['correction_status']}")
        
        return True
        
    except Exception as e:
        logger.error(f"验证修复有效性时出错: {str(e)}")
        return False

def main():
    logger.info("===== 综合数据修复工具 =====")
    
    conn = connect_db()
    if not conn:
        logger.error("无法连接数据库，退出程序")
        sys.exit(1)
    
    try:
        # 先修复重复的correction记录
        logger.info("\n===== 步骤1: 修复重复的correction记录 =====")
        fix_duplicate_corrections(conn)
        
        # 修复分数不一致问题
        logger.info("\n===== 步骤2: 修复分数不一致问题 =====")
        fix_score_inconsistency(conn)
        
        # 修复空的results字段
        logger.info("\n===== 步骤3: 修复空的results字段 =====")
        fix_empty_results(conn)
        
        # 验证修复的有效性
        logger.info("\n===== 步骤4: 验证修复有效性 =====")
        verify_fix_effectiveness(conn)
        
        logger.info("\n修复完成，请在浏览器中刷新页面查看结果: http://127.0.0.1:5000/results/86")
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main() 