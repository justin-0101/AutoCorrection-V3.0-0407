#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import datetime
from flask import Flask
from app.models.task_status import TaskStatus
from app.extensions import db
from sqlalchemy import desc, asc

app = Flask(__name__)
app.config.from_object('app.config.Config')
db.init_app(app)

def check_tasks_status():
    with app.app_context():
        # 获取所有失败的任务
        print("\n=== 失败任务详情 ===")
        failed_tasks = TaskStatus.query.filter(TaskStatus.status == "FAILURE").order_by(desc(TaskStatus.created_at)).all()
        
        if not failed_tasks:
            print("没有失败的任务")
        else:
            print(f"找到 {len(failed_tasks)} 个失败的任务:")
            for task in failed_tasks:
                print("\n任务详情:")
                print(f"  任务ID: {task.task_id}")
                print(f"  任务名称: {task.task_name}")
                print(f"  状态: {task.status}")
                print(f"  关联类型: {task.related_type}")
                print(f"  关联ID: {task.related_id}")
                print(f"  创建时间: {task.created_at}")
                print(f"  开始时间: {task.started_at}")
                print(f"  完成时间: {task.completed_at}")
                
                if task.error_details:
                    try:
                        error_details = json.loads(task.error_details)
                        print("  错误详情:")
                        for key, value in error_details.items():
                            print(f"    {key}: {value}")
                    except json.JSONDecodeError:
                        print(f"  错误详情: {task.error_details}")
                else:
                    print("  错误详情: 无")
        
        # 获取活跃的任务（等待中和正在运行）
        print("\n=== 活跃任务详情 ===")
        active_tasks = TaskStatus.query.filter(
            (TaskStatus.status == "PENDING") | (TaskStatus.status == "STARTED")
        ).order_by(asc(TaskStatus.created_at)).all()
        
        if not active_tasks:
            print("没有活跃的任务")
        else:
            print(f"找到 {len(active_tasks)} 个活跃的任务:")
            for task in active_tasks:
                print("\n任务详情:")
                print(f"  任务ID: {task.task_id}")
                print(f"  任务名称: {task.task_name}")
                print(f"  状态: {task.status}")
                print(f"  关联类型: {task.related_type}")
                print(f"  关联ID: {task.related_id}")
                print(f"  创建时间: {task.created_at}")
                print(f"  开始时间: {task.started_at or '未开始'}")

if __name__ == '__main__':
    check_tasks_status() 