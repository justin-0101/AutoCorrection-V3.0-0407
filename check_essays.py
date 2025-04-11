#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import create_app
from app.models.essay import Essay, EssayStatus

def check_essays_status():
    print('初始化应用...')
    app = create_app()
    
    print('打开应用上下文...')
    with app.app_context():
        # 获取所有作文
        essays = Essay.query.all()
        print(f'总共有 {len(essays)} 篇作文')
        
        # 显示所有作文的状态
        for e in essays:
            print(f'ID: {e.id}, 标题: {e.title}, 状态: {e.status}')
        
        # 查看待批改的作文
        pending_essays = Essay.query.filter(Essay.status != EssayStatus.COMPLETED.value).all()
        print(f'\n待批改作文: {len(pending_essays)} 篇')
        for e in pending_essays:
            print(f'ID: {e.id}, 标题: {e.title}, 状态: {e.status}')

if __name__ == '__main__':
    check_essays_status() 