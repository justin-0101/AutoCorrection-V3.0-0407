#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from app import create_app
from app.models.essay import Essay
from app.models.correction import Correction

def check_status():
    app = create_app()
    
    with app.app_context():
        # 检查作文状态
        essay = Essay.query.get(1)
        if essay:
            print(f'作文状态: {essay.status}')
            print(f'作文标题: {essay.title}')
            print(f'批改结果: {essay.corrected_content if essay.corrected_content else "尚未批改"}')
            
            # 检查批改任务状态
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            if correction:
                print(f'批改任务状态: {correction.status}')
                print(f'任务ID: {correction.task_id}')
                if correction.error_message:
                    print(f'错误信息: {correction.error_message}')
            else:
                print('未找到相关批改任务')
        else:
            print('未找到作文')

if __name__ == '__main__':
    check_status() 