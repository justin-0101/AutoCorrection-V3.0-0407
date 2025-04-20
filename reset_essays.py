#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重置卡住的作文状态
"""

from app import create_app
from app.models.essay import Essay, EssayStatus
from app.extensions import db
from datetime import datetime, timedelta

def reset_stuck_essays():
    """重置所有处于CORRECTING状态的作文"""
    print("开始重置卡住的作文...")
    
    app = create_app()
    with app.app_context():
        # 查找所有处于CORRECTING状态的作文
        stuck_essays = Essay.query.filter_by(status=EssayStatus.CORRECTING.value).all()
        
        print(f"找到卡住的作文数量: {len(stuck_essays)}")
        if not stuck_essays:
            print("没有找到卡住的作文")
            return
        
        # 打印所有卡住的作文ID
        essay_ids = [e.id for e in stuck_essays]
        print(f"卡住的作文ID列表: {essay_ids}")
        
        # 重置所有卡住的作文状态
        reset_count = 0
        for essay in stuck_essays:
            try:
                print(f"重置作文 ID: {essay.id}, 原状态: {essay.status}, 更新时间: {essay.updated_at}")
                essay.status = EssayStatus.PENDING.value
                essay.error_message = "系统自动重置卡住的作文状态"
                reset_count += 1
            except Exception as e:
                print(f"重置作文 {essay.id} 状态时出错: {str(e)}")
        
        # 提交更改
        db.session.commit()
        print(f"成功重置 {reset_count} 个卡住的作文")

if __name__ == "__main__":
    reset_stuck_essays() 