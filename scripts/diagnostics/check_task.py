#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查作文批改状态脚本
"""

import os
import sys
from datetime import datetime
import inspect

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 导入应用
from app import create_app
from app.models.essay import Essay
from app.models.correction import Correction
from app.models.essay_status import EssayStatus
from app.models.correction_status import CorrectionStatus
from app.tasks.celery_app import celery_app

app = create_app()

def check_essay_status():
    """检查最近的作文和批改状态"""
    with app.app_context():
        # 获取最近提交的作文
        recent_essays = Essay.query.order_by(Essay.id.desc()).limit(5).all()
        
        print("\n最近的作文状态:")
        print("=" * 50)
        print("{:<5} {:<15} {:<15} {:<20} {:<15}".format("ID", "标题", "状态", "创建时间", "来源"))
        print("-" * 50)
        
        for essay in recent_essays:
            created_at = essay.created_at.strftime("%Y-%m-%d %H:%M") if essay.created_at else "N/A"
            print("{:<5} {:<15} {:<15} {:<20} {:<15}".format(
                essay.id, 
                essay.title[:12] + "..." if len(essay.title) > 12 else essay.title, 
                essay.status,
                created_at,
                essay.source_type
            ))
        
        # 查看批改情况
        print("\n批改记录:")
        print("=" * 60)
        print("{:<5} {:<5} {:<10} {:<15} {:<20}".format("ID", "作文ID", "状态", "得分", "批改时间"))
        print("-" * 60)
        
        for essay in recent_essays:
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            if correction:
                completed_at = correction.completed_at.strftime("%Y-%m-%d %H:%M") if correction.completed_at else "N/A"
                print("{:<5} {:<5} {:<10} {:<15} {:<20}".format(
                    correction.id,
                    essay.id,
                    correction.status,
                    str(correction.score) if correction.score is not None else "N/A",
                    completed_at
                ))
            else:
                print("{:<5} {:<5} {:<10} {:<15} {:<20}".format(
                    "N/A",
                    essay.id,
                    "无批改记录",
                    "N/A",
                    "N/A"
                ))
        
        # 获取指定的作文
        print("\n最近上传的作文 ID=3:")
        essay_3 = Essay.query.get(3)
        if essay_3:
            correction_3 = Correction.query.filter_by(essay_id=3).first()
            print(f"作文标题: {essay_3.title}")
            print(f"作文状态: {essay_3.status}")
            print(f"批改状态: {correction_3.status if correction_3 else '无批改记录'}")
            
            # 检查Correction模型属性
            if correction_3:
                print("\nCorrection模型字段:")
                for attr in dir(correction_3):
                    if not attr.startswith('_') and not callable(getattr(correction_3, attr)):
                        value = getattr(correction_3, attr)
                        print(f"  - {attr}: {value}")
                
                # 检查是否有celery任务ID
                # 尝试几个可能的属性名
                celery_task_id = None
                for attr_name in ['celery_task_id', 'task_id', 'async_task_id', 'async_id']:
                    if hasattr(correction_3, attr_name):
                        celery_task_id = getattr(correction_3, attr_name)
                        if celery_task_id:
                            print(f"\n找到任务ID: {attr_name} = {celery_task_id}")
                            
                            # 检查任务状态
                            try:
                                from celery.result import AsyncResult
                                task = AsyncResult(celery_task_id, app=celery_app)
                                print(f"任务状态: {task.state}")
                                print(f"任务信息: {task.info}")
                            except Exception as e:
                                print(f"获取任务状态失败: {str(e)}")
                            break
                
                if not celery_task_id:
                    print("\n未找到Celery任务ID")
        else:
            print("未找到ID=3的作文")

if __name__ == "__main__":
    check_essay_status() 