#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查特定ID的作文是否存在
"""

from app import create_app
from app.models.essay import Essay
from app.models.correction import Correction
from app.models.db import db

def check_essay():
    """检查数据库中是否存在特定ID的作文"""
    app = create_app()
    
    with app.app_context():
        print("开始检查数据库中的作文记录...")
        
        # 检查ID为8的作文
        essay_id = 8
        essay = Essay.query.filter_by(id=essay_id).first()
        
        if essay:
            print(f"找到ID为{essay_id}的作文:")
            print(f"  - 标题: {essay.title}")
            print(f"  - 状态: {essay.status}")
            print(f"  - 用户ID: {essay.user_id}")
            print(f"  - 创建时间: {essay.created_at}")
            
            # 检查关联的批改记录
            correction = Correction.query.filter_by(essay_id=essay_id).first()
            if correction:
                print(f"找到关联的批改记录:")
                print(f"  - ID: {correction.id}")
                print(f"  - 状态: {correction.status}")
                print(f"  - 任务ID: {correction.task_id}")
                print(f"  - is_deleted: {correction.is_deleted}")
            else:
                print(f"未找到关联的批改记录")
        else:
            print(f"未找到ID为{essay_id}的作文")
            
            # 列出所有最近的作文
            print("\n最近的5篇作文:")
            recent_essays = Essay.query.order_by(Essay.id.desc()).limit(5).all()
            
            if recent_essays:
                for e in recent_essays:
                    if e is not None:
                        print(f"  - ID: {e.id}, 标题: {e.title}, 状态: {e.status}")
                    else:
                        print("  - 发现一个空的Essay对象")
            else:
                print("数据库中没有作文记录")
            
            # 检查最新创建的所有作文
            print("\n检查所有作文记录:")
            all_essays = Essay.query.all()
            essays_count = len(all_essays) if all_essays else 0
            print(f"数据库中共有 {essays_count} 篇作文")
            
            if all_essays:
                print("\n所有作文ID列表:")
                for e in all_essays:
                    if e is not None:
                        print(f"  - ID: {e.id}")

if __name__ == "__main__":
    check_essay() 