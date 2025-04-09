#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
为待处理作文创建批改记录
为系统中所有pending状态但没有批改记录的作文创建批改记录
"""

import os
import sys
import time
from datetime import datetime

# 确保工作目录正确
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
os.chdir(project_root)
sys.path.insert(0, project_root)

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus
from app.models.essay import Essay, EssayStatus
from app.models.db import db

def create_correction_records():
    """为所有待处理作文创建批改记录"""
    app = create_app()
    
    with app.app_context():
        # 查找所有pending状态的作文
        pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING.value).all()
        
        print(f"找到 {len(pending_essays)} 篇待处理作文")
        
        if not pending_essays:
            print("没有待处理的作文")
            return
        
        created_count = 0
        for essay in pending_essays:
            # 检查是否已有批改记录
            existing_correction = Correction.query.filter_by(essay_id=essay.id).first()
            
            if existing_correction:
                print(f"作文ID {essay.id} 已有批改记录，跳过")
                continue
            
            # 创建新的批改记录
            try:
                correction = Correction(
                    essay_id=essay.id,
                    status=CorrectionStatus.PENDING.value,
                    created_at=time.time(),
                    updated_at=time.time()
                )
                db.session.add(correction)
                db.session.commit()
                created_count += 1
                print(f"为作文ID {essay.id} 创建批改记录成功")
            except Exception as e:
                db.session.rollback()
                print(f"为作文ID {essay.id} 创建批改记录失败: {str(e)}")
        
        print(f"\n共为 {created_count} 篇作文创建了批改记录")

def main():
    try:
        create_correction_records()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"创建批改记录时出错: {str(e)}")

if __name__ == "__main__":
    main() 