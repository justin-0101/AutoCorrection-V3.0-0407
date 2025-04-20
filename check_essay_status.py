#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查所有作文的状态分布
"""

from app import create_app
from app.models.essay import Essay, EssayStatus
from app.extensions import db
from collections import Counter

def check_essay_status():
    """检查所有作文状态的分布情况"""
    print("开始检查作文状态分布...")
    
    app = create_app()
    with app.app_context():
        # 获取所有作文
        all_essays = Essay.query.all()
        
        # 统计各状态数量
        status_counts = Counter([e.status for e in all_essays])
        
        # 打印统计结果
        print(f"总作文数量: {len(all_essays)}")
        print("\n状态分布:")
        for status, count in status_counts.items():
            display_text = EssayStatus.get_display_text(status)
            print(f"{status} ({display_text}): {count}")
        
        # 检查各状态的作文
        for status in EssayStatus:
            essays = Essay.query.filter_by(status=status.value).all()
            if essays:
                print(f"\n{status.value} 状态的作文ID:")
                for essay in essays:
                    print(f"ID: {essay.id}, 标题: {essay.title[:30]}..., 更新时间: {essay.updated_at}")

if __name__ == "__main__":
    check_essay_status() 