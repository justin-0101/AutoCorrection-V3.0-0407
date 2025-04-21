#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
手动处理一篇待批改的作文
"""

from app import create_app
from app.models.essay import Essay, EssayStatus
from app.core.correction.correction_service import CorrectionService
from app.extensions import db

# 创建应用实例和上下文
app = create_app()

with app.app_context():
    # 初始化批改服务
    print("初始化批改服务...")
    service = CorrectionService()
    
    # 获取待处理的作文
    essay_id = 107  # 这里手动指定要处理的作文ID
    print(f"获取作文ID: {essay_id}")
    
    # 确保没有活跃事务
    if db.session.in_transaction():
        print("检测到活跃事务，回滚...")
        db.session.rollback()
    
    essay = Essay.query.get(essay_id)
    
    if not essay:
        print(f"找不到ID为{essay_id}的作文")
    else:
        print(f"找到作文: '{essay.title}', 当前状态: {essay.status}")
        
        # 执行批改
        print("开始执行批改...")
        try:
            # 确保没有活跃事务
            if db.session.in_transaction():
                print("检测到活跃事务，回滚...")
                db.session.rollback()
                
            result = service.perform_correction(essay)
            print(f"批改完成，结果: {result}")
        except Exception as e:
            print(f"批改过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 确保错误后回滚任何可能的事务
            if db.session.in_transaction():
                print("回滚事务...")
                db.session.rollback()
        
        # 检查作文最新状态
        essay = Essay.query.get(essay_id)
        print(f"批改后作文状态: {essay.status}") 