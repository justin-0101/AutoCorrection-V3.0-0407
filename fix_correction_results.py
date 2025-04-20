#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批改结果修复工具 - 精简版
用于诊断和修复批改结果表中的问题，特别是修复results字段为空或包含无效数据的记录
"""

import os
import json
import sqlite3
from datetime import datetime
import traceback
import sys
import re
import random

def connect_db():
    """连接数据库"""
    db_path = "instance/essay_correction.db"
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件 {db_path} 不存在!")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 设置行工厂，使结果可以通过列名访问
        print(f"成功连接到数据库: {db_path}")
        return conn
    except Exception as e:
        print(f"连接数据库出错: {e}")
        return None

def check_essay_record(conn, essay_id):
    """检查指定essay_id的记录"""
    try:
        cur = conn.cursor()
        
        # 检查essay_id的记录
        print(f"\n----- 检查essay_id={essay_id}的记录 -----")
        cur.execute("SELECT id, title, content, status, score, created_at, updated_at FROM essays WHERE id=?;", (essay_id,))
        essay = cur.fetchone()
        
        if not essay:
            print(f"未找到ID为{essay_id}的作文记录!")
            return None, None
        else:
            print(f"找到ID为{essay_id}的作文记录:")
            print(f"标题: {essay['title']}")
            print(f"状态: {essay['status']}")
            print(f"得分: {essay['score']}")
            print(f"内容长度: {len(essay['content'])} 字符")
            print(f"创建时间: {essay['created_at']}")
            print(f"修改时间: {essay['updated_at']}")
        
        # 检查corrections表中相关记录
        print(f"\n----- 检查corrections表中essay_id={essay_id}的记录 -----")
        cur.execute("SELECT id, status, score, task_id, is_deleted, created_at, updated_at FROM corrections WHERE essay_id=? AND is_deleted=0;", (essay_id,))
        correction = cur.fetchone()
        
        if not correction:
            print(f"未找到essay_id={essay_id}的有效批改记录!")
            return essay, None
        else:
            print(f"批改记录ID: {correction['id']}")
            print(f"状态: {correction['status']}")
            print(f"得分: {correction['score']}")
            print(f"任务ID: {correction['task_id']}")
            print(f"创建时间: {correction['created_at']}")
            print(f"修改时间: {correction['updated_at']}")
            
            # 检查results字段
            cur.execute("SELECT results FROM corrections WHERE id=?", (correction['id'],))
            result_data = cur.fetchone()
            results = result_data['results'] if result_data else None
            
            if results:
                try:
                    results_json = json.loads(results)
                    print(f"批改结果JSON数据有效，包含{len(results_json)}个字段")
                    for key in results_json.keys():
                        print(f"  - {key}")
                except json.JSONDecodeError as e:
                    print(f"警告: 批改结果JSON数据无效! 错误: {e}")
            else:
                print("警告: 批改结果为空!")
            
        return essay, correction
    except Exception as e:
        print(f"检查记录出错: {e}")
        traceback.print_exc()
        return None, None

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
        "level": level,
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

def fix_correction_result(conn, essay_id):
    """修复批改结果"""
    try:
        cur = conn.cursor()
        
        # 获取essay信息
        cur.execute("SELECT * FROM essays WHERE id=?", (essay_id,))
        essay = cur.fetchone()
        
        if not essay:
            print(f"未找到ID为{essay_id}的作文记录，无法修复!")
            return False
        
        # 获取correction记录
        cur.execute("SELECT * FROM corrections WHERE essay_id=? AND is_deleted=0 ORDER BY id DESC LIMIT 1", (essay_id,))
        correction = cur.fetchone()
        
        if not correction:
            print(f"未找到essay_id={essay_id}的有效批改记录，无法修复!")
            return False
        
        # 检查results字段
        needs_fix = False
        if not correction['results']:
            print("批改结果为空，需要修复")
            needs_fix = True
        else:
            try:
                results_json = json.loads(correction['results'])
                if len(results_json) < 3:
                    print("批改结果数据不完整，需要修复")
                    needs_fix = True
                else:
                    print("批改结果完整，无需修复")
            except json.JSONDecodeError:
                print("批改结果JSON数据无效，需要修复")
                needs_fix = True
        
        if needs_fix:
            print("开始创建模拟批改结果...")
            
            # 使用correction中的score作为基准，如果没有则使用essay中的score
            score = None
            if correction['score'] and correction['score'] > 0:
                score = correction['score']
            elif essay['score'] and essay['score'] > 0:
                score = essay['score']
            
            # 创建DeepSeek格式的模拟结果
            mock_result = create_mock_deepseek_result(essay['content'], score)
            
            # 处理评语和建议等字段
            comments = correction['comments'] or mock_result["总体评价"]
            error_analysis = correction['error_analysis'] or json.dumps({
                "content_analysis": mock_result["内容分析"],
                "language_analysis": mock_result["语言分析"],
                "structure_analysis": mock_result["结构分析"],
                "spelling_errors": mock_result["错别字"]
            }, ensure_ascii=False)
            improvement_suggestions = correction['improvement_suggestions'] or mock_result["写作建议"]
            
            # 更新最终分数（确保有一个有效的分数）
            final_score = score or mock_result["总得分"]
            
            # 更新批改记录
            print(f"正在更新批改记录(ID={correction['id']})...")
            cur.execute("""
                UPDATE corrections 
                SET results=?, status='completed', updated_at=?, 
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
                correction['id']
            ))
            
            # 更新essay记录
            print(f"正在更新作文记录(ID={essay_id})...")
            cur.execute("""
                UPDATE essays 
                SET status='completed', updated_at=?, 
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
            print(f"已成功修复essay_id={essay_id}的批改结果")
            return True
        else:
            print(f"essay_id={essay_id}的批改结果无需修复")
            return True
    except Exception as e:
        print(f"修复批改结果出错: {e}")
        traceback.print_exc()
        conn.rollback()
        return False

def main():
    print("===== 批改结果修复工具 2.0 =====")
    
    # 连接数据库
    conn = connect_db()
    if not conn:
        print("无法连接数据库，退出程序。")
        return
    
    try:
        # 获取要处理的essay_id
        essay_id = 86
        if len(sys.argv) > 1:
            try:
                essay_id = int(sys.argv[1])
            except ValueError:
                print(f"无效的essay_id: {sys.argv[1]}，使用默认值: 86")
        
        # 检查记录
        essay, correction = check_essay_record(conn, essay_id)
        if not essay:
            print("未找到作文记录，退出程序。")
            return
        
        # 修复批改结果
        print(f"\n----- 开始修复essay_id={essay_id}的批改结果 -----")
        if fix_correction_result(conn, essay_id):
            print(f"essay_id={essay_id}的批改结果修复完成")
            
            # 验证修复结果
            print(f"\n----- 验证修复结果 -----")
            check_essay_record(conn, essay_id)
            
            print(f"\n请刷新页面 http://127.0.0.1:5000/results/{essay_id} 查看结果。")
        else:
            print(f"essay_id={essay_id}的批改结果修复失败。")
    
    except Exception as e:
        print(f"程序执行出错: {e}")
        traceback.print_exc()
    
    finally:
        if conn:
            conn.close()
            print("数据库连接已关闭")

if __name__ == "__main__":
    main() 