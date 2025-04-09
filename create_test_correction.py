#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建一个测试批改任务
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus, CorrectionType
from app.models.essay import Essay, EssayStatus
from app.models.db import db

def create_test_correction():
    """创建一个测试批改任务"""
    with app.app_context():
        try:
            # 查找一个草稿状态的作文
            essay = Essay.query.filter_by(status=EssayStatus.DRAFT.value).first()
            
            if not essay:
                print("未找到草稿状态的作文，创建一个新的...")
                # 查找一个用户
                from app.models.user import User
                user = User.query.first()
                
                if not user:
                    print("未找到用户，请先创建一个用户")
                    return False
                
                # 创建一个新的作文
                essay = Essay(
                    title="测试作文 - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    content="这是一篇测试作文，用于测试批改功能。",
                    user_id=user.id,
                    status=EssayStatus.DRAFT.value,
                    source_type="text"
                )
                db.session.add(essay)
                db.session.commit()
                print(f"已创建新作文，ID={essay.id}")
            
            # 检查是否已经有该作文的批改
            existing_correction = Correction.query.filter_by(
                essay_id=essay.id,
                status=CorrectionStatus.PENDING.value
            ).first()
            
            if existing_correction:
                print(f"该作文(ID={essay.id})已有待处理的批改，ID={existing_correction.id}")
                return existing_correction
            
            # 创建一个新的批改任务
            correction = Correction(
                essay_id=essay.id,
                type=CorrectionType.AI.value,
                status=CorrectionStatus.PENDING.value,
                is_deleted=False
            )
            
            db.session.add(correction)
            
            # 更新作文状态
            essay.status = EssayStatus.PENDING.value
            
            db.session.commit()
            
            print(f"已创建新的批改任务，ID={correction.id}，作文ID={essay.id}")
            return correction
            
        except Exception as e:
            print(f"创建测试批改任务时出错: {str(e)}")
            db.session.rollback()
            return None

if __name__ == "__main__":
    # 创建应用实例
    app = create_app()
    
    # 创建测试批改任务
    correction = create_test_correction()
    
    if correction:
        print("测试批改任务创建成功！")
        print(f"批改ID: {correction.id}")
        print(f"作文ID: {correction.essay_id}")
        print(f"状态: {correction.status}")
    else:
        print("测试批改任务创建失败！") 