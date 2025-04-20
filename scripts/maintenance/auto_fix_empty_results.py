#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动修复空批改结果的定时任务脚本
用于定期检查数据库中批改结果为空或无效的记录并进行修复
"""

import os
import sys
import json
import sqlite3
import logging
import random
import re
from datetime import datetime, timedelta
import traceback

# 确保系统路径正确，可以导入应用模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_fix_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = 'instance/essay_correction.db'

def connect_db():
    """连接到数据库"""
    if not os.path.exists(DB_PATH):
        logger.error(f"错误: 数据库文件 {DB_PATH} 不存在")
        return None

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        logger.info(f"成功连接到数据库: {DB_PATH}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"错误: 无法连接到数据库: {e}")
        return None

def create_mock_deepseek_result(content, score=None):
    """
    创建符合DeepSeek格式的模拟批改结果
    
    Args:
        content: 作文内容
        score: 指定分数，如果为None则根据内容长度生成
        
    Returns:
        Dict: 模拟的批改结果
    """
    # 基于内容长度生成分数
    content_length = len(content)
    if score is None:
        base_score = 35  # 基础分数
        # 内容越长，分数越高，最高50分
        length_factor = min(content_length / 1000, 1.0)  # 长度因子，最高1.0
        total_score = min(base_score + int(length_factor * 15), 50)
        # 随机波动
        total_score = max(min(total_score + random.randint(-3, 3), 50), 30)
    else:
        total_score = score
    
    # 分项得分
    content_score = int(total_score * 0.35)
    language_score = int(total_score * 0.3)
    structure_score = int(total_score * 0.2)
    writing_score = int(total_score * 0.15)
    
    # 确保总分等于各项分数之和
    adjustment = total_score - (content_score + language_score + structure_score + writing_score)
    content_score += adjustment
    
    # 找出一些可能的拼写错误（简单模拟）
    words = re.findall(r'[\u4e00-\u9fa5]+', content)
    potential_errors = []
    if len(words) > 100:
        for i in range(min(3, len(words) // 100)):
            if len(words) > 0:
                index = random.randint(0, len(words) - 1)
                if len(words[index]) > 1:
                    wrong = words[index]
                    correct = wrong  # 在真实场景中这里应该是修正的单词
                    potential_errors.append(f"{wrong}->{correct}")
    
    # 根据总分确定等级
    if total_score >= 43:
        level = "A"
        overall_assessment = "这是一篇出色的作文，内容立意明确，中心突出，材料具体生动，有真情实感；语言得体、流畅；结构严谨，注意照应，详略得当。"
    elif total_score >= 35:
        level = "B"
        overall_assessment = "这是一篇优秀的作文，内容立意明确，中心突出，材料具体；语言规范、通顺；结构完整，条理清楚。"
    elif total_score >= 27:
        level = "C" 
        overall_assessment = "这是一篇中等水平的作文，内容立意基本明确，材料能表现中心；语言基本通顺；结构基本完整，有条理。"
    else:
        level = "D"
        overall_assessment = "这篇作文内容立意不够明确，材料较难表现中心；语言不够通顺；结构不够完整，条理性有待提高。"
    
    # 创建DeepSeek格式的结果
    mock_result = {
        "总得分": total_score,
        "分项得分": {
            "内容主旨": content_score,
            "语言文采": language_score,
            "文章结构": structure_score,
            "文面书写": writing_score
        },
        "总体评价": overall_assessment,
        "内容分析": f"文章主题{'明确' if total_score >= 35 else '基本明确' if total_score >= 27 else '不够明确'}，{'思想深刻，论述充分' if total_score >= 43 else '有一定的思想深度' if total_score >= 35 else '思想深度有待提高'}。{'材料具体生动，有真情实感' if total_score >= 43 else '材料较为具体' if total_score >= 35 else '材料能基本表现中心' if total_score >= 27 else '材料难以充分表现中心'}。",
        "语言分析": f"语言表达{'流畅生动，修辞丰富' if total_score >= 43 else '规范流畅' if total_score >= 35 else '基本通顺' if total_score >= 27 else '有待改进'}，{'用词准确，句式多样化' if total_score >= 43 else '用词较为准确' if total_score >= 35 else '用词基本恰当' if total_score >= 27 else '用词不够准确'}。",
        "结构分析": f"文章结构{'严谨完整，详略得当，过渡自然' if total_score >= 43 else '完整，条理清晰' if total_score >= 35 else '基本完整，有一定条理' if total_score >= 27 else '不够完整，条理性有待提高'}。",
        "写作建议": f"{'建议在保持现有水平的基础上，进一步提高语言的表现力和文章的感染力。' if total_score >= 43 else '建议进一步丰富内容细节，增强语言表现力，使文章更有感染力。' if total_score >= 35 else '建议明确文章主题，丰富内容细节，提高语言表达的准确性和流畅性。' if total_score >= 27 else '建议明确文章主题，增加内容的深度和广度，改进语言表达，注意文章结构的完整性。'}",
        "错别字": potential_errors,
        "是否模拟": True,
        "模拟原因": "由于原批改结果丢失或无效，系统生成的模拟结果"
    }
    
    # 添加英文键以兼容不同客户端
    mock_result.update({
        "total_score": total_score,
        "grade": level,
        "level": level,
        "word_count": content_length,
        "content_score": content_score,
        "language_score": language_score,
        "structure_score": structure_score,
        "writing_score": writing_score,
        "overall_assessment": mock_result["总体评价"],
        "content_analysis": mock_result["内容分析"],
        "language_analysis": mock_result["语言分析"],
        "structure_analysis": mock_result["结构分析"],
        "improvement_suggestions": mock_result["写作建议"],
        "spelling_errors": mock_result["错别字"],
        "is_mock": True,
        "mock_reason": "由于原批改结果丢失或无效，系统生成的模拟结果"
    })
    
    return mock_result

def find_empty_or_invalid_results(conn, days_ago=7):
    """
    查找最近N天内批改结果为空或无效的记录
    
    Args:
        conn: 数据库连接
        days_ago: 最近几天内的记录
    
    Returns:
        List: 需要修复的记录列表，包含essay_id和correction_id
    """
    logger.info(f"开始查找最近{days_ago}天内批改结果为空或无效的记录")
    cutoff_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    cursor = conn.cursor()
    records_to_fix = []
    
    try:
        # 查找状态为completed但results为空或无效的记录
        cursor.execute("""
            SELECT c.id, c.essay_id, c.score, c.results, e.title, e.content
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
            results = record['results']
            
            needs_fix = False
            # 检查results是否为空
            if not results:
                logger.warning(f"correction_id={correction_id} (essay_id={essay_id}) 批改结果为空")
                needs_fix = True
            else:
                # 检查results是否为有效JSON
                try:
                    results_json = json.loads(results)
                    # 检查results是否完整（至少包含总得分和分项得分）
                    if not (('总得分' in results_json or 'total_score' in results_json) and 
                           ('分项得分' in results_json or ('content_score' in results_json and 'language_score' in results_json))):
                        logger.warning(f"correction_id={correction_id} (essay_id={essay_id}) 批改结果数据不完整")
                        needs_fix = True
                except json.JSONDecodeError:
                    logger.warning(f"correction_id={correction_id} (essay_id={essay_id}) 批改结果JSON无效")
                    needs_fix = True
            
            if needs_fix:
                records_to_fix.append({
                    'correction_id': correction_id,
                    'essay_id': essay_id,
                    'score': record['score'],
                    'title': record['title'],
                    'content': record['content']
                })
        
        logger.info(f"发现{len(records_to_fix)}条需要修复的记录")
        return records_to_fix
        
    except sqlite3.Error as e:
        logger.error(f"查询数据库错误: {e}")
        return []

def fix_record(conn, record):
    """
    修复单条批改记录
    
    Args:
        conn: 数据库连接
        record: 需要修复的记录信息
    
    Returns:
        bool: 是否修复成功
    """
    correction_id = record['correction_id']
    essay_id = record['essay_id']
    content = record['content']
    
    logger.info(f"开始修复 correction_id={correction_id} (essay_id={essay_id})")
    cursor = conn.cursor()
    
    try:
        # 使用原有分数或根据内容生成模拟分数
        score = record['score'] if record['score'] and record['score'] > 0 else None
        
        # 创建模拟批改结果
        mock_result = create_mock_deepseek_result(content, score)
        
        # 获取原有的评语等字段
        cursor.execute("""
            SELECT comments, error_analysis, improvement_suggestions 
            FROM corrections 
            WHERE id = ?
        """, (correction_id,))
        
        correction_data = cursor.fetchone()
        
        # 处理评语和建议等字段
        comments = correction_data['comments'] or mock_result["总体评价"]
        error_analysis = correction_data['error_analysis'] or json.dumps({
            "content_analysis": mock_result["内容分析"],
            "language_analysis": mock_result["语言分析"],
            "structure_analysis": mock_result["结构分析"],
            "spelling_errors": mock_result["错别字"]
        }, ensure_ascii=False)
        improvement_suggestions = correction_data['improvement_suggestions'] or mock_result["写作建议"]
        
        # 更新最终分数（确保有一个有效的分数）
        final_score = score or mock_result["总得分"]
        
        # 更新批改记录
        logger.info(f"更新批改记录 correction_id={correction_id}")
        cursor.execute("""
            UPDATE corrections 
            SET results=?, updated_at=?, 
                score=?, comments=?, error_analysis=?, 
                improvement_suggestions=?
            WHERE id=?
        """, (
            json.dumps(mock_result, ensure_ascii=False),
            datetime.now().isoformat(),
            final_score,
            comments,
            error_analysis,
            improvement_suggestions,
            correction_id
        ))
        
        # 更新essay记录
        logger.info(f"更新作文记录 essay_id={essay_id}")
        cursor.execute("""
            UPDATE essays 
            SET updated_at=?, 
                score=?, comments=?, error_analysis=?, 
                improvement_suggestions=?
            WHERE id=?
        """, (
            datetime.now().isoformat(),
            final_score,
            comments,
            error_analysis,
            improvement_suggestions,
            essay_id
        ))
        
        conn.commit()
        logger.info(f"成功修复 correction_id={correction_id} (essay_id={essay_id})")
        return True
    
    except Exception as e:
        logger.error(f"修复 correction_id={correction_id} (essay_id={essay_id}) 失败: {e}")
        logger.error(traceback.format_exc())
        conn.rollback()
        return False

def auto_fix_empty_results(days_ago=7, dry_run=False):
    """
    自动修复最近N天内批改结果为空或无效的记录
    
    Args:
        days_ago: 最近几天内的记录
        dry_run: 如果为True，只检查不修改
    
    Returns:
        Dict: 包含修复结果的字典
    """
    logger.info(f"开始自动修复最近{days_ago}天内的空批改结果")
    
    # 连接数据库
    conn = connect_db()
    if not conn:
        logger.error("无法连接数据库，退出")
        return {
            'status': 'error',
            'message': '无法连接数据库',
            'fixed_count': 0,
            'failed_count': 0,
            'total_count': 0
        }
    
    try:
        # 查找需要修复的记录
        records_to_fix = find_empty_or_invalid_results(conn, days_ago)
        
        if not records_to_fix:
            logger.info("未发现需要修复的记录")
            return {
                'status': 'success',
                'message': '未发现需要修复的记录',
                'fixed_count': 0,
                'failed_count': 0,
                'total_count': 0
            }
        
        if dry_run:
            logger.info(f"dry_run模式: 发现{len(records_to_fix)}条需要修复的记录，但不执行修复")
            return {
                'status': 'dry_run',
                'message': f'发现{len(records_to_fix)}条需要修复的记录',
                'records': records_to_fix,
                'fixed_count': 0,
                'failed_count': 0,
                'total_count': len(records_to_fix)
            }
        
        # 执行修复
        fixed_count = 0
        failed_count = 0
        
        for record in records_to_fix:
            if fix_record(conn, record):
                fixed_count += 1
            else:
                failed_count += 1
        
        logger.info(f"修复完成: 成功修复{fixed_count}条记录，失败{failed_count}条记录")
        
        return {
            'status': 'success',
            'message': f'成功修复{fixed_count}条记录，失败{failed_count}条记录',
            'fixed_count': fixed_count,
            'failed_count': failed_count,
            'total_count': len(records_to_fix)
        }
            
    except Exception as e:
        logger.error(f"自动修复过程中发生错误: {e}")
        logger.error(traceback.format_exc())
        return {
            'status': 'error',
            'message': f'自动修复过程中发生错误: {str(e)}',
            'fixed_count': 0,
            'failed_count': 0,
            'total_count': 0
        }
    
    finally:
        if conn:
            conn.close()
            logger.info("数据库连接已关闭")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='自动修复空批改结果')
    parser.add_argument('--days', type=int, default=7, help='最近几天内的记录')
    parser.add_argument('--dry-run', action='store_true', help='只检查不修改')
    args = parser.parse_args()
    
    logger.info(f"启动自动修复工具: 检查最近{args.days}天内的记录, dry_run={args.dry_run}")
    
    result = auto_fix_empty_results(days_ago=args.days, dry_run=args.dry_run)
    
    if result['status'] == 'error':
        logger.error(f"自动修复失败: {result['message']}")
        return 1
    
    logger.info(f"自动修复完成: {result['message']}")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 