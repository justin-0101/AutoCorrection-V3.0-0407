#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import sqlite3
import json
import time
from datetime import datetime

def connect_db():
    """连接到数据库"""
    db_path = 'instance/essay_correction.db'
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件 {db_path} 不存在!")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        print(f"成功连接到数据库: {db_path}")
        return conn
    except Exception as e:
        print(f"连接数据库失败: {str(e)}")
        return None

def fix_duplicate_corrections(conn, essay_id):
    """修复同一篇文章的重复correction记录"""
    try:
        # 获取指定essay_id的所有correction记录
        cur = conn.cursor()
        cur.execute('SELECT id, essay_id, score, status, results, created_at, updated_at FROM corrections WHERE essay_id = ?', 
                   (essay_id,))
        corrections = cur.fetchall()
        
        if not corrections:
            print(f"未找到essay_id={essay_id}的correction记录")
            return False
            
        if len(corrections) == 1:
            print(f"essay_id={essay_id}只有一条correction记录，无需修复")
            return True
            
        print(f"发现essay_id={essay_id}有{len(corrections)}条correction记录")
        
        # 显示现有记录
        for corr in corrections:
            print(f"correction_id={corr['id']}, score={corr['score']}, status={corr['status']}")
            
        # 获取essay表中的分数
        cur.execute('SELECT id, score, status FROM essays WHERE id = ?', (essay_id,))
        essay = cur.fetchone()
        
        if not essay:
            print(f"错误: 未找到id={essay_id}的essay记录")
            return False
            
        print(f"essay_id={essay['id']}, score={essay['score']}, status={essay['status']}")
        
        # 以essay表的分数和状态为准，更新所有correction记录
        essay_score = essay['score'] or 0
        essay_status = essay['status']
        
        # 准备更新数据
        now = datetime.now().isoformat()
        
        # 只保留第一条记录，删除其他记录
        first_correction_id = corrections[0]['id']
        other_correction_ids = [c['id'] for c in corrections[1:]]
        
        # 更新第一条记录
        cur.execute('''
            UPDATE corrections 
            SET score = ?, status = ?, updated_at = ?
            WHERE id = ?
        ''', (essay_score, essay_status, now, first_correction_id))
        
        print(f"已更新correction_id={first_correction_id}的记录: score={essay_score}, status={essay_status}")
        
        # 删除其他记录(为了不破坏可能存在的外键约束，使用软删除标记为已删除)
        for corr_id in other_correction_ids:
            cur.execute('''
                UPDATE corrections 
                SET is_deleted = 1, updated_at = ?
                WHERE id = ?
            ''', (now, corr_id))
            print(f"已标记correction_id={corr_id}的记录为已删除")
        
        # 提交更改
        conn.commit()
        print("所有更改已提交到数据库")
        return True
        
    except Exception as e:
        print(f"修复重复correction记录时出错: {str(e)}")
        return False

def main():
    print("===== 重复批改记录修复工具 =====")
    
    # 连接数据库
    conn = connect_db()
    if not conn:
        sys.exit(1)
        
    # 修复essay_id=86的重复correction记录
    essay_id = 86
    result = fix_duplicate_corrections(conn, essay_id)
    
    if result:
        print(f"\n完成! essay_id={essay_id}的重复correction记录已修复")
        print("请在浏览器中刷新页面查看结果: http://127.0.0.1:5000/results/86")
    else:
        print(f"\n错误! 无法修复essay_id={essay_id}的重复correction记录")
    
    conn.close()

if __name__ == "__main__":
    main() 