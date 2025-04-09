#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试任务提交脚本
用于测试任务状态跟踪功能
"""

import os
import sys
import time
from datetime import datetime

# 确保系统路径正确
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.tasks.notification_tasks import send_task_failure_notification
from app.tasks.monitoring_tasks import update_queue_length_metrics

def submit_test_task():
    """提交测试任务"""
    print(f"提交测试任务，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        # 提交通知任务
        notification_task = send_task_failure_notification.delay(
            task_id='test-task-id',
            related_type='test',
            related_id='123',
            error_message='这是一个测试错误消息'
        )
        print(f"通知任务已提交，任务ID: {notification_task.id}")
        
        # 提交监控任务
        monitoring_task = update_queue_length_metrics.delay()
        print(f"监控任务已提交，任务ID: {monitoring_task.id}")
        
        # 等待任务完成
        print("\n等待任务执行完成...")
        for _ in range(10):
            time.sleep(1)
            notification_status = notification_task.state
            monitoring_status = monitoring_task.state
            print(f"通知任务状态: {notification_status}, 监控任务状态: {monitoring_status}")
            
            if notification_status in ['SUCCESS', 'FAILURE'] and monitoring_status in ['SUCCESS', 'FAILURE']:
                break
        
        # 打印任务结果
        print("\n任务执行结果:")
        print(f"通知任务: {notification_task.state}")
        if notification_task.successful():
            print(f"结果: {notification_task.result}")
        else:
            print(f"错误: {notification_task.traceback}")
            
        print(f"\n监控任务: {monitoring_task.state}")
        if monitoring_task.successful():
            print(f"结果: {monitoring_task.result}")
        else:
            print(f"错误: {monitoring_task.traceback}")
        
        # 提示使用任务状态查询工具
        print("\n可使用以下命令查看任务状态记录:")
        print(f"python check_task_status.py --task-id {notification_task.id}")
        print(f"python check_task_status.py --task-id {monitoring_task.id}")
        print("python check_task_status.py --stats")

if __name__ == "__main__":
    submit_test_task() 