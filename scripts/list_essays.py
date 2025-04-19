#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
列出最近的作文记录
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.extensions import db
from app.models.essay import Essay
from app.models.correction import Correction

# 创建应用实例
app = create_app()

def main():
    """列出最近的作文及其状态"""
    with app.app_context():
        # 查询最近的10篇作文
        essays = Essay.query.order_by(Essay.id.desc()).limit(10).all()
        
        if not essays:
            print("数据库中没有作文记录")
            return
        
        print(f"数据库中共有 {Essay.query.count()} 篇作文")
        print("\n最近10篇作文:")
        print("-" * 80)
        print(f"{'ID':<5} {'标题':<30} {'状态':<10} {'提交时间':<20} {'分数':<5}")
        print("-" * 80)
        
        for essay in essays:
            # 查询对应的批改结果
            correction = Correction.query.filter_by(essay_id=essay.id).order_by(Correction.id.desc()).first()
            score_val = correction.score if correction and hasattr(correction, 'score') and correction.score is not None else "N/A"
            
            # 限制标题长度并处理None值
            title = essay.title if essay.title else "无标题"
            title = title[:28]
            
            # 格式化提交时间
            created_at = essay.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(essay, 'created_at') and essay.created_at else "N/A"
            
            # 获取正确的状态字段
            status = essay.status if hasattr(essay, 'status') else "未知状态"

            print(f"{essay.id:<5} {title:<30} {status:<10} {created_at:<20} {str(score_val):<5}")

if __name__ == "__main__":
    main() 