#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查待批改作文
显示当前系统中待批改作文的状态
"""

import os
import sys
from datetime import datetime

# 确保工作目录正确
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
os.chdir(project_root)
sys.path.insert(0, project_root)

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus
from app.models.essay import Essay, EssayStatus

def check_pending_essays():
    """检查待批改的作文"""
    app = create_app()
    
    with app.app_context():
        # 查找所有待处理的批改任务
        pending_corrections = Correction.query.filter_by(
            status=CorrectionStatus.PENDING.value
        ).all()
        
        print(f"====== 待批改作文 ({len(pending_corrections)}) ======")
        
        if not pending_corrections:
            print("当前没有待处理的批改任务")
            return
        
        for i, correction in enumerate(pending_corrections):
            essay_id = correction.essay_id
            essay = Essay.query.get(essay_id)
            
            if not essay:
                print(f"{i+1}. 批改ID: {correction.id} - 未找到对应作文(ID={essay_id})")
                continue
            
            created_time = datetime.fromtimestamp(correction.created_at).strftime('%Y-%m-%d %H:%M:%S') if correction.created_at else "未知"
            
            print(f"{i+1}. 作文ID: {essay_id}")
            print(f"   标题: {essay.title}")
            print(f"   作文状态: {essay.status}")
            print(f"   批改状态: {correction.status}")
            print(f"   创建时间: {created_time}")
            print(f"   任务ID: {correction.task_id or '未分配'}")
            print()

def main():
    try:
        check_pending_essays()
    except Exception as e:
        print(f"检查待批改作文时出错: {str(e)}")

if __name__ == "__main__":
    main() 