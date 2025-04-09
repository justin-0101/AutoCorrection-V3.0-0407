#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查批改任务的状态
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入应用
from app import create_app
from app.models.correction import Correction
from app.models.essay import Essay

def check_correction_status():
    """检查批改任务的状态"""
    with app.app_context():
        try:
            # 获取所有批改任务
            corrections = Correction.query.all()
            
            print(f"总共找到 {len(corrections)} 个批改任务:")
            for correction in corrections:
                essay = Essay.query.get(correction.essay_id)
                essay_title = essay.title if essay else "未知"
                
                print(f"批改ID: {correction.id}")
                print(f"作文ID: {correction.essay_id}")
                print(f"作文标题: {essay_title}")
                print(f"类型: {correction.type}")
                print(f"状态: {correction.status}")
                print(f"任务ID: {correction.task_id}")
                print(f"创建时间: {correction.created_at}")
                print(f"更新时间: {correction.updated_at}")
                print(f"完成时间: {correction.completed_at}")
                print(f"重试次数: {correction.retry_count}")
                print(f"错误信息: {correction.error_message}")
                print("-" * 50)
            
        except Exception as e:
            print(f"检查批改任务状态时出错: {str(e)}")

if __name__ == "__main__":
    # 创建应用实例
    app = create_app()
    
    # 检查批改任务状态
    check_correction_status() 