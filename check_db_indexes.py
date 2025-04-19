#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查数据库索引和数据一致性
"""

import os
import sqlite3
import json
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
        print(f"数据库连接错误: {e}")
        return None

def check_indexes(conn):
    """检查与corrections和essays表相关的索引"""
    print("===== 检查数据库索引 =====")
    cursor = conn.cursor()
    
    # 查询所有corrections表相关的索引
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND (name LIKE '%correction%' OR name LIKE '%essay%')")
    indexes = cursor.fetchall()
    
    if not indexes:
        print("没有找到与corrections或essays表相关的索引")
    else:
        print(f"找到 {len(indexes)} 个相关索引:")
        for idx in indexes:
            print(f"- 名称: {idx['name']}")
            print(f"  定义: {idx['sql']}")
            print()

def check_inconsistencies(conn):
    """检查essays和corrections表中的数据不一致情况"""
    print("\n===== 检查数据不一致问题 =====")
    cursor = conn.cursor()
    
    # 获取所有已完成的essays
    cursor.execute("""
        SELECT id, title, score, comments, status, created_at, updated_at
        FROM essays
        WHERE status = 'completed'
    """)
    essays = cursor.fetchall()
    
    print(f"找到 {len(essays)} 篇已完成的作文")
    
    inconsistencies = []
    
    for essay in essays:
        essay_id = essay['id']
        
        # 获取对应的correction记录
        cursor.execute("""
            SELECT id, score, comments, status, created_at, updated_at
            FROM corrections
            WHERE essay_id = ? AND status = 'completed'
            ORDER BY id DESC LIMIT 1
        """, (essay_id,))
        correction = cursor.fetchone()
        
        if not correction:
            inconsistencies.append({
                'essay_id': essay_id,
                'problem': '缺少对应的批改记录',
                'details': f"essay.title: {essay['title']}"
            })
            continue
            
        # 检查分数是否一致
        if essay['score'] != correction['score']:
            inconsistencies.append({
                'essay_id': essay_id,
                'problem': '分数不一致',
                'details': f"correction: {correction['score']}, essay: {essay['score']}"
            })
            
        # 检查评语是否一致
        essay_comments = essay['comments'] or ""
        correction_comments = correction['comments'] or ""
        
        if essay_comments != correction_comments:
            inconsistencies.append({
                'essay_id': essay_id,
                'problem': '评语不一致',
                'details': f"correction: {len(correction_comments)} 字符, essay: {len(essay_comments)} 字符"
            })
    
    # 打印不一致问题
    if inconsistencies:
        print(f"\n找到 {len(inconsistencies)} 条不一致记录:")
        for issue in inconsistencies:
            print(f"- essay_id={issue['essay_id']}, 问题: {issue['problem']}, 详情: {issue['details']}")
    else:
        print("\n没有发现数据不一致问题！所有记录匹配。")

def check_data_integrity(conn):
    """检查数据完整性和重复记录"""
    print("\n===== 检查数据完整性 =====")
    cursor = conn.cursor()
    
    # 检查是否有重复的批改记录
    cursor.execute("""
        SELECT essay_id, COUNT(*) as count
        FROM corrections
        WHERE status = 'completed'
        GROUP BY essay_id
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"\n找到 {len(duplicates)} 篇作文有多条批改记录:")
        for dup in duplicates:
            essay_id = dup['essay_id']
            cursor.execute("""
                SELECT id, created_at, updated_at, version
                FROM corrections
                WHERE essay_id = ? AND status = 'completed'
                ORDER BY id
            """, (essay_id,))
            corrections = cursor.fetchall()
            
            print(f"- essay_id={essay_id}, 共有 {dup['count']} 条批改记录:")
            for corr in corrections:
                print(f"  * id={corr['id']}, 创建时间={corr['created_at']}, 更新时间={corr['updated_at']}, 版本={corr['version']}")
    else:
        print("没有发现重复的批改记录。")
    
    # 检查可能的孤立记录（没有对应作文的批改）
    cursor.execute("""
        SELECT c.id, c.essay_id
        FROM corrections c
        LEFT JOIN essays e ON c.essay_id = e.id
        WHERE e.id IS NULL
    """)
    orphans = cursor.fetchall()
    
    if orphans:
        print(f"\n找到 {len(orphans)} 条孤立的批改记录:")
        for orphan in orphans:
            print(f"- correction_id={orphan['id']}, 引用了不存在的 essay_id={orphan['essay_id']}")
    else:
        print("\n没有发现孤立的批改记录。")

def suggest_fixes(conn, inconsistencies):
    """提出修复数据不一致问题的建议"""
    print("\n===== 建议修复措施 =====")
    
    # 检查是否有缺少唯一索引的情况
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uix_corrections_essay_id'")
    if not cursor.fetchone():
        print("建议: 添加唯一索引约束到corrections表的essay_id列:")
        print("  CREATE UNIQUE INDEX uix_corrections_essay_id ON corrections(essay_id) WHERE status = 'completed';")
        
    # 如果有不一致记录，提供修复脚本
    if inconsistencies:
        print("\n自动修复数据不一致问题的SQL脚本样例:")
        print("BEGIN TRANSACTION;")
        
        for issue in inconsistencies:
            essay_id = issue['essay_id']
            if issue['problem'] == '分数不一致' or issue['problem'] == '评语不一致':
                print(f"-- 修复 essay_id={essay_id} 的不一致问题")
                print(f"UPDATE essays SET ")
                print(f"  score = (SELECT score FROM corrections WHERE essay_id = {essay_id} AND status = 'completed' ORDER BY id DESC LIMIT 1),")
                print(f"  comments = (SELECT comments FROM corrections WHERE essay_id = {essay_id} AND status = 'completed' ORDER BY id DESC LIMIT 1)")
                print(f"WHERE id = {essay_id};")
        
        print("COMMIT;")

def main():
    """主函数"""
    print("===== 数据库索引和一致性检查工具 =====")
    conn = connect_db()
    if not conn:
        return
    
    try:
        # 检查索引
        check_indexes(conn)
        
        # 检查数据一致性
        check_inconsistencies(conn)
        
        # 检查数据完整性
        check_data_integrity(conn)
        
        # 提出修复建议
        # 暂时注释掉，因为需要inconsistencies变量的值
        # suggest_fixes(conn, inconsistencies)
        
    finally:
        conn.close()

    print("\n检查完成。如果发现了问题，请根据上述建议进行修复。")

if __name__ == "__main__":
    main() 