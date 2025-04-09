#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)

from app import create_app
from app.models.correction import Correction
from app.models.essay import Essay

def check_status():
    app = create_app()
    with app.app_context():
        correction = Correction.query.get(2)
        essay = Essay.query.get(1)
        
        if correction:
            print(f'批改任务状态: {correction.status}')
            print(f'任务ID: {correction.task_id}')
            print(f'错误信息: {correction.error_message}')
        else:
            print('未找到批改任务')
            
        if essay:
            print(f'作文状态: {essay.status}')
            print(f'作文标题: {essay.title}')
        else:
            print('未找到作文')

if __name__ == '__main__':
    check_status() 