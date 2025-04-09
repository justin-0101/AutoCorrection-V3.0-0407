from flask import Flask
from app import create_app
from app.models import TaskStatus
from sqlalchemy import func

app = create_app()

with app.app_context():
    # 查询处于'pending'状态的任务数量
    pending_count = TaskStatus.query.filter_by(status='pending').count()
    print(f"活跃待处理任务数量: {pending_count}")
    
    # 获取所有任务状态的统计
    print("\n所有任务状态统计:")
    status_counts = TaskStatus.query.with_entities(TaskStatus.status, func.count(TaskStatus.id)).group_by(TaskStatus.status).all()
    
    if status_counts:
        for status, count in status_counts:
            print(f"- {status}: {count}")
    else:
        print("- 数据库中没有任务记录") 