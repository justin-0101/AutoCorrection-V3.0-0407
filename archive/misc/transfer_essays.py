import sqlite3
import json
import os
from datetime import datetime

print("开始将essay_history表的数据转移到essays表...")

# 连接数据库
DB_PATH = 'instance/essay_correction.db'
if not os.path.exists(DB_PATH):
    print(f"数据库文件不存在: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 查询essay_history表中的记录
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    cursor.execute("""
        SELECT essay_id, user_id, title, original_text, created_at, score, corrected_text, feedback
        FROM essay_history
    """)
    
    history_records = cursor.fetchall()
    print(f"在essay_history表中找到 {len(history_records)} 条记录")
    
    transferred_count = 0
    
    for record in history_records:
        essay_id, user_id, title, content, created_at, score, corrected_text, feedback_json = record
        
        # 检查essays表中是否已有此记录（防止重复）
        cursor.execute("""
            SELECT COUNT(*) FROM essays 
            WHERE user_id = ? AND title = ? AND submission_time = ?
        """, (user_id, title, created_at))
        
        if cursor.fetchone()[0] > 0:
            print(f"跳过已存在的记录: ID={essay_id}, 标题={title}")
            continue
            
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 解析评分结果JSON
            feedback = json.loads(feedback_json) if feedback_json else {}
            
            # 从feedback中提取字段，如果不存在则使用默认值
            grade = feedback.get('等级', 'C-中等')
            content_score = feedback.get('内容分', 10)
            language_score = feedback.get('表达分', 8)
            structure_score = feedback.get('结构分', 6)
            writing_score = feedback.get('书写分', 3)
            overall_assessment = feedback.get('总体评价', '无总体评价')
            content_analysis = feedback.get('内容分析', '无内容分析')
            language_analysis = feedback.get('表达分析', '无表达分析')
            structure_analysis = feedback.get('结构分析', '无结构分析')
            writing_analysis = feedback.get('书写分析', '无书写分析')
            spelling_errors = json.dumps(feedback.get('错别字', {"解析": []}), ensure_ascii=False)
            word_count = len(content)
            
            # 插入记录到essays表
            cursor.execute("""
                INSERT INTO essays (
                    user_id, title, content, submission_time, word_count,
                    total_score, grade, content_score, language_score,
                    structure_score, writing_score, spelling_errors,
                    overall_assessment, content_analysis, language_analysis,
                    structure_analysis, writing_analysis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, title, content, created_at, word_count,
                score, grade, content_score, language_score,
                structure_score, writing_score, spelling_errors,
                overall_assessment, content_analysis, language_analysis,
                structure_analysis, writing_analysis
            ))
            
            transferred_count += 1
            print(f"成功转移记录: ID={essay_id}, 标题={title}")
            
        except Exception as e:
            print(f"转移记录出错 (ID={essay_id}): {str(e)}")
            
    conn.commit()
    print(f"\n完成! 成功转移 {transferred_count} 条记录")
    
except Exception as e:
    print(f"查询essay_history表出错: {str(e)}")
    
finally:
    conn.close() 