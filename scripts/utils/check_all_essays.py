#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查所有作文状态
显示系统中所有状态的作文信息
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

def format_timestamp(timestamp):
    """格式化时间戳为可读格式"""
    if not timestamp:
        return "未知"
    
    # 如果是datetime对象，直接格式化
    if isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    # 如果是浮点数或整数，转换为datetime再格式化
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return str(timestamp)

def check_all_essays():
    """检查所有作文状态"""
    app = create_app()
    
    with app.app_context():
        # 获取所有作文
        all_essays = Essay.query.order_by(Essay.id.desc()).limit(20).all()
        
        print(f"====== 最近20篇作文 ======")
        
        if not all_essays:
            print("系统中没有作文")
            return
        
        for i, essay in enumerate(all_essays):
            # 查找对应的批改信息
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            
            print(f"{i+1}. 作文ID: {essay.id}")
            print(f"   标题: {essay.title}")
            print(f"   作文状态: {essay.status}")
            print(f"   创建时间: {format_timestamp(essay.created_at)}")
            
            if correction:
                print(f"   批改状态: {correction.status}")
                print(f"   批改创建时间: {format_timestamp(correction.created_at)}")
                print(f"   任务ID: {correction.task_id or '未分配'}")
            else:
                print(f"   无批改记录")
            print()

        # 获取批改状态计数
        correction_stats = {}
        for status in CorrectionStatus:
            count = Correction.query.filter_by(status=status.value).count()
            correction_stats[status.name] = count
        
        print("====== 批改状态统计 ======")
        for status, count in correction_stats.items():
            print(f"{status}: {count}篇")

def main():
    try:
        check_all_essays()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"检查作文状态时出错: {str(e)}")

if __name__ == "__main__":
    main() 