#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # 修改这里，直接使用scripts的父目录
os.chdir(project_root)  # 切换工作目录
sys.path.insert(0, project_root)

from app import create_app
from app.models.essay import Essay
from app.models.db import db

def create_test_essay():
    app = create_app()
    with app.app_context():
        try:
            # 创建测试作文
            essay = Essay(
                title='测试作文',
                content='这是一篇测试作文，用于测试批改功能。',
                user_id=1,
                status='pending'
            )
            db.session.add(essay)
            db.session.commit()
            print(f'创建测试作文成功，ID: {essay.id}')
            
            # 创建批改任务
            from app.models.correction import Correction
            correction = Correction(
                essay_id=essay.id,
                status='pending'
            )
            db.session.add(correction)
            db.session.commit()
            print(f'创建批改任务成功，ID: {correction.id}')
            
        except Exception as e:
            print(f'发生错误: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    create_test_essay() 