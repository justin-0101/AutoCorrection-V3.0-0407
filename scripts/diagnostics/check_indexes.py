#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
临时脚本：检查task_statuses表索引
"""

from app import create_app
from app.models import db
from sqlalchemy import inspect

def check_task_status_indexes():
    """检查task_statuses表的索引情况"""
    app = create_app()
    
    with app.app_context():
        # 获取表检查器
        inspector = inspect(db.engine)
        
        # 获取表格列表
        tables = inspector.get_table_names()
        print(f"数据库中的表: {tables}")
        
        # 检查task_statuses表是否存在
        if 'task_statuses' in tables:
            print("task_statuses表存在于数据库中")
            
            # 获取task_statuses表的索引
            indexes = inspector.get_indexes('task_statuses')
            print(f"task_statuses表的索引数量: {len(indexes)}")
            
            # 打印每个索引的详细信息
            for idx, index in enumerate(indexes):
                print(f"\n索引 #{idx+1}: {index['name']}")
                print(f"  列: {index['column_names']}")
                print(f"  唯一: {index.get('unique', False)}")
        else:
            print("task_statuses表不存在于数据库中")

if __name__ == "__main__":
    check_task_status_indexes() 