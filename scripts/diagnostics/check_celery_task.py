#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查Celery任务状态脚本
"""

import os
import sys
from datetime import datetime
import json

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 导入应用
from app import create_app
from app.tasks.celery_app import celery_app
from celery.result import AsyncResult
from app.models.correction import Correction
from app.models.essay import Essay

app = create_app()

def check_celery_task(task_id):
    """检查Celery任务状态"""
    with app.app_context():
        try:
            # 创建任务结果对象
            result = AsyncResult(task_id, app=celery_app)
            
            # 输出任务基本信息
            print(f"\n任务ID: {task_id}")
            print(f"任务状态: {result.state}")
            print(f"任务信息: {result.info}")
            
            # 如果任务成功，输出结果
            if result.successful():
                print("\n任务结果:")
                print("-" * 50)
                try:
                    if isinstance(result.result, dict):
                        for key, value in result.result.items():
                            print(f"{key}: {value}")
                    else:
                        print(result.result)
                except Exception as e:
                    print(f"无法显示任务结果: {e}")
            
            # 检查数据库中的批改记录
            correction = Correction.query.filter_by(task_id=task_id).first()
            if correction:
                print("\n数据库中的批改记录:")
                print("-" * 50)
                print(f"批改ID: {correction.id}")
                print(f"批改类型: {correction.type}")
                print(f"批改状态: {correction.status}")
                print(f"作文ID: {correction.essay_id}")
                print(f"创建时间: {correction.created_at}")
                print(f"更新时间: {correction.updated_at}")
                print(f"完成时间: {correction.completed_at}")
                print(f"重试次数: {correction.retry_count}")
                
                # 检查作文状态
                essay = Essay.query.get(correction.essay_id)
                if essay:
                    print("\n关联作文状态:")
                    print("-" * 50)
                    print(f"作文标题: {essay.title}")
                    print(f"作文状态: {essay.status}")
            else:
                print("\n未找到与该任务ID关联的批改记录")
            
        except Exception as e:
            print(f"检查任务状态时出错: {e}")

def list_recent_tasks():
    """列出最近的批改任务"""
    with app.app_context():
        try:
            # 获取最近的批改记录
            corrections = Correction.query.filter(Correction.task_id.isnot(None)).order_by(Correction.created_at.desc()).limit(5).all()
            
            if not corrections:
                print("未找到任何带有任务ID的批改记录")
                return
            
            print("\n最近的批改任务:")
            print("=" * 70)
            print("{:<36} {:<10} {:<15} {:<10}".format("任务ID", "状态", "作文ID", "创建时间"))
            print("-" * 70)
            
            for correction in corrections:
                created_at = correction.created_at.strftime("%Y-%m-%d %H:%M") if correction.created_at else "N/A"
                print("{:<36} {:<10} {:<15} {:<10}".format(
                    correction.task_id or "无任务ID",
                    correction.status,
                    correction.essay_id,
                    created_at
                ))
                
                # 检查任务状态
                if correction.task_id:
                    try:
                        result = AsyncResult(correction.task_id, app=celery_app)
                        print(f"    Celery任务状态: {result.state}")
                    except Exception as e:
                        print(f"    无法获取Celery任务状态: {e}")
            
        except Exception as e:
            print(f"列出最近任务时出错: {e}")

def check_essay_task(essay_id):
    """根据作文ID检查批改任务"""
    with app.app_context():
        try:
            # 获取作文信息
            essay = Essay.query.get(essay_id)
            if not essay:
                print(f"未找到ID为{essay_id}的作文")
                return
            
            print(f"\n作文ID: {essay_id}, 标题: {essay.title}")
            print(f"作文状态: {essay.status}")
            
            # 查找与该作文关联的批改记录
            correction = Correction.query.filter_by(essay_id=essay_id).first()
            if correction:
                print(f"\n批改ID: {correction.id}")
                print(f"批改状态: {correction.status}")
                print(f"任务ID: {correction.task_id or '无任务ID'}")
                
                # 如果有任务ID，检查任务状态
                if correction.task_id:
                    try:
                        result = AsyncResult(correction.task_id, app=celery_app)
                        print(f"\nCelery任务状态: {result.state}")
                        print(f"任务信息: {result.info}")
                    except Exception as e:
                        print(f"无法获取Celery任务状态: {e}")
            else:
                print("未找到与该作文关联的批改记录")
            
        except Exception as e:
            print(f"检查作文任务时出错: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list" or sys.argv[1] == "-l":
            list_recent_tasks()
        elif sys.argv[1] == "--essay" or sys.argv[1] == "-e":
            if len(sys.argv) > 2:
                check_essay_task(int(sys.argv[2]))
            else:
                print("请提供作文ID")
        else:
            check_celery_task(sys.argv[1])
    else:
        print("用法:")
        print("  python check_celery_task.py <task_id>   # 检查指定任务ID的状态")
        print("  python check_celery_task.py --list      # 列出最近的批改任务")
        print("  python check_celery_task.py --essay <essay_id>  # 检查指定作文的批改任务")