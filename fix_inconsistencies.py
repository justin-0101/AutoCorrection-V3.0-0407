#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复essays和corrections表中的数据不一致问题
"""

import os
import sqlite3
import json
import sys
import traceback
from datetime import datetime

DB_PATH = 'instance/essay_correction.db'

def connect_db():
    """连接到数据库"""
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库文件 {DB_PATH} 不存在")
        return None

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"错误: 无法连接到数据库: {e}")
        return None

def fix_inconsistencies(conn):
    """修复essays和corrections表中的数据不一致情况"""
    print("\n===== 修复数据不一致问题 =====")
    cursor = conn.cursor()
    
    try:
        # 获取所有已完成的作文
        cursor.execute("""
            SELECT id, title, score, comments, error_analysis, improvement_suggestions
            FROM essays
            WHERE status = 'completed'
        """)
        completed_essays = cursor.fetchall()
        
        if not completed_essays:
            print("未找到已完成的作文")
            return
            
        print(f"找到 {len(completed_essays)} 篇已完成的作文")
        
        success_count = 0
        fail_count = 0
        
        for essay in completed_essays:
            essay_id = essay['id']
            title = essay['title']
            
            try:
                # 检查是否有对应的批改记录
                cursor.execute("""
                    SELECT id, score, comments, error_analysis, improvement_suggestions, status
                    FROM corrections
                    WHERE essay_id = ? AND status = 'completed' AND is_deleted = 0
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (essay_id,))
                correction = cursor.fetchone()
                
                if not correction:
                    print(f"警告: essay_id={essay_id} ('{title}') 没有对应的已完成批改记录")
                    continue
                
                # 检查分数是否一致
                score_mismatch = False
                if essay['score'] != correction['score']:
                    score_mismatch = True
                
                # 检查评语是否一致
                comments_mismatch = False
                if essay['comments'] != correction['comments']:
                    comments_mismatch = True
                    
                # 检查错误分析是否一致
                error_analysis_mismatch = False
                if essay['error_analysis'] != correction['error_analysis']:
                    error_analysis_mismatch = True
                    
                # 检查改进建议是否一致
                improvement_suggestions_mismatch = False
                if essay['improvement_suggestions'] != correction['improvement_suggestions']:
                    improvement_suggestions_mismatch = True
                
                # 如果有不一致，进行修复
                if any([score_mismatch, comments_mismatch, error_analysis_mismatch, improvement_suggestions_mismatch]):
                    # 记录具体的不一致项
                    mismatch_details = []
                    if score_mismatch:
                        mismatch_details.append(f"分数(correction={correction['score']}, essay={essay['score']})")
                    if comments_mismatch:
                        mismatch_details.append("评语不一致")
                    if error_analysis_mismatch:
                        mismatch_details.append("错误分析不一致")
                    if improvement_suggestions_mismatch:
                        mismatch_details.append("改进建议不一致")
                    
                    print(f"修复: essay_id={essay_id} ('{title}') - 不一致项: {', '.join(mismatch_details)}")
                    
                    # 更新essay表中的字段以匹配corrections表
                    try:
                        cursor.execute("""
                            UPDATE essays
                            SET score = ?,
                                comments = ?,
                                error_analysis = ?,
                                improvement_suggestions = ?,
                                updated_at = ?
                            WHERE id = ?
                        """, (
                            correction['score'] or 0,  # 确保分数不为None
                            correction['comments'] or "",  # 确保评语不为None
                            correction['error_analysis'] or "",  # 确保错误分析不为None
                            correction['improvement_suggestions'] or "",  # 确保改进建议不为None
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            essay_id
                        ))
                        conn.commit()
                        print(f"修复: essay_id={essay_id} ('{title}') - 已更新")
                        success_count += 1
                    except sqlite3.Error as e:
                        print(f"错误: 无法修复 essay_id={essay_id} - {e}")
                        conn.rollback()
                        fail_count += 1
                else:
                    # 记录已经一致的记录
                    print(f"检查: essay_id={essay_id} ('{title}') - 数据已一致")
            except Exception as e:
                print(f"错误: 处理 essay_id={essay_id} 时发生异常: {e}")
                traceback.print_exc()
                fail_count += 1
                
        print(f"\n修复完成: 成功修复 {success_count} 条记录, {fail_count} 条记录修复失败")
        
    except sqlite3.Error as e:
        print(f"错误: 查询数据库时出错: {e}")
        conn.rollback()
    finally:
        cursor.close()

def create_unique_index(conn):
    """为corrections表创建唯一索引"""
    print("\n===== 创建唯一索引 =====")
    cursor = conn.cursor()
    
    try:
        # 先检查是否有多条completed状态的记录对应同一个essay_id
        cursor.execute("""
            SELECT essay_id, COUNT(*) as count
            FROM corrections
            WHERE status = 'completed' AND is_deleted = 0
            GROUP BY essay_id
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"\n找到 {len(duplicates)} 篇作文有多条completed批改记录，需要处理后才能创建唯一索引")
            
            for duplicate in duplicates:
                essay_id = duplicate['essay_id']
                print(f"处理 essay_id={essay_id} 的重复记录...")
                
                # 获取这个essay_id的所有completed批改记录
                cursor.execute("""
                    SELECT id, created_at, updated_at
                    FROM corrections
                    WHERE essay_id = ? AND status = 'completed' AND is_deleted = 0
                    ORDER BY created_at DESC
                """, (essay_id,))
                records = cursor.fetchall()
                
                # 保留最新的一条，将其他的标记为archived
                if len(records) > 1:
                    for i, record in enumerate(records):
                        if i > 0:  # 跳过第一条记录（最新的）
                            try:
                                cursor.execute("""
                                    UPDATE corrections
                                    SET status = 'archived', updated_at = ?
                                    WHERE id = ?
                                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), record['id']))
                                print(f"  - correction_id={record['id']} 已标记为archived")
                            except sqlite3.Error as e:
                                print(f"  - 错误: 无法更新 correction_id={record['id']}: {e}")
                                conn.rollback()
            
            conn.commit()
        
        # 检查是否存在valid_correction_status CHECK约束
        cursor.execute("PRAGMA table_info(corrections)")
        columns = cursor.fetchall()
        constraints = []
        for col in columns:
            if col['name'] == 'status':
                constraints_str = col.get('dflt_value') or ""
                if 'CHECK' in constraints_str.upper():
                    constraints.append(constraints_str)
        
        # 如果存在约束，需要先移除
        if constraints:
            print(f"发现status列存在约束条件: {constraints}")
            print("需要先修改表结构以移除约束...")
            
            # 创建临时表并复制数据
            try:
                # 获取表结构
                cursor.execute("PRAGMA table_info(corrections)")
                columns = cursor.fetchall()
                column_defs = []
                for col in columns:
                    # 跳过CHECK约束
                    if col['name'] == 'status':
                        column_defs.append(f"`{col['name']}` {col['type']}")
                    else:
                        column_defs.append(f"`{col['name']}` {col['type']}{' NOT NULL' if col['notnull'] else ''}{' DEFAULT ' + col['dflt_value'] if col['dflt_value'] else ''}")
                
                # 创建临时表
                cursor.execute(f"""
                    CREATE TABLE corrections_temp (
                        {', '.join(column_defs)}
                    )
                """)
                
                # 复制数据
                cursor.execute("INSERT INTO corrections_temp SELECT * FROM corrections")
                
                # 删除原表
                cursor.execute("DROP TABLE corrections")
                
                # 重命名临时表
                cursor.execute("ALTER TABLE corrections_temp RENAME TO corrections")
                
                print("成功移除约束条件")
                conn.commit()
            except sqlite3.Error as e:
                print(f"错误: 移除约束条件失败: {e}")
                conn.rollback()
                return
        
        # 尝试创建唯一索引
        try:
            # 检查索引是否已存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_corrections_essay_completed'")
            if cursor.fetchone():
                print("唯一索引已存在，无需创建")
            else:
                cursor.execute("""
                    CREATE UNIQUE INDEX idx_corrections_essay_completed
                    ON corrections (essay_id)
                    WHERE status = 'completed' AND is_deleted = 0
                """)
                print("成功创建唯一索引")
                conn.commit()
        except sqlite3.Error as e:
            print(f"错误: 无法创建唯一索引 - {e}")
            conn.rollback()
    
    except sqlite3.Error as e:
        print(f"错误: 查询数据库时出错: {e}")
        conn.rollback()
    finally:
        cursor.close()

def handle_orphaned_corrections(conn):
    """处理孤立的批改记录"""
    print("\n===== 处理孤立批改记录 =====")
    cursor = conn.cursor()
    
    try:
        # 查找没有对应essay的correction记录
        cursor.execute("""
            SELECT c.id, c.essay_id, c.status, c.created_at
            FROM corrections c
            LEFT JOIN essays e ON c.essay_id = e.id
            WHERE e.id IS NULL AND c.is_deleted = 0
        """)
        orphaned = cursor.fetchall()
        
        if not orphaned:
            print("未找到孤立的批改记录")
            return
            
        print(f"找到 {len(orphaned)} 条孤立的批改记录")
        
        for record in orphaned:
            try:
                # 标记为已删除
                cursor.execute("""
                    UPDATE corrections
                    SET is_deleted = 1, updated_at = ?
                    WHERE id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), record['id']))
                print(f"标记删除 correction_id={record['id']}")
            except sqlite3.Error as e:
                print(f"错误: 无法标记删除 correction_id={record['id']}: {e}")
                conn.rollback()
        
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"错误: 查询数据库时出错: {e}")
        conn.rollback()
    finally:
        cursor.close()

def main():
    """主函数"""
    print("===== 数据一致性修复工具 =====")
    conn = connect_db()
    if not conn:
        return
    
    try:
        # 修复数据不一致
        fix_inconsistencies(conn)
        
        # 创建唯一索引
        create_unique_index(conn)
        
        # 处理孤立记录
        handle_orphaned_corrections(conn)
        
    finally:
        conn.close()

    print("\n所有修复操作已完成，请重新启动应用以确保更改生效。")

if __name__ == "__main__":
    main() 