#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
处理待处理的批改任务
该脚本查找所有状态为pending的批改记录，并将其提交到Celery任务队列
"""

import os
import sys
from datetime import datetime
import time
import uuid

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus
from app.models.essay import Essay, EssayStatus
from app.tasks.correction_tasks import process_essay_correction
from app.tasks.celery_app import celery_app

app = create_app()

def process_pending_corrections():
    """处理所有待处理的批改任务"""
    with app.app_context():
        # 只处理ID为4的作文
        correction = Correction.query.filter_by(id=4).first()
        
        if not correction:
            print("未找到ID为4的批改任务")
            return
        
        essay_id = correction.essay_id
        essay = Essay.query.get(essay_id)
        
        if not essay:
            print(f"未找到作文 ID={essay_id}，跳过")
            return
        
        print(f"处理作文 ID={essay_id}, 标题: {essay.title}")
        
        # 更新状态为correcting
        correction.status = CorrectionStatus.CORRECTING.value
        essay.status = EssayStatus.CORRECTING.value
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        correction.task_id = task_id
        
        # 提交到数据库
        from app.models.db import db
        db.session.commit()
        
        try:
            # 发送到Celery任务队列
            task_result = process_essay_correction.delay(essay_id)
            print(f"  - 任务已提交，任务ID: {task_result.id}")
            
            # 保存实际的Celery任务ID
            correction.task_id = task_result.id
            db.session.commit()
            
            print(f"  - 成功: 作文 ID={essay_id} 已提交到任务队列")
            
        except Exception as e:
            print(f"  - 错误: 提交任务失败: {str(e)}")
            
            # 更新状态为失败
            correction.status = CorrectionStatus.FAILED.value
            correction.error_message = f"提交任务失败: {str(e)}"
            essay.status = EssayStatus.FAILED.value
            db.session.commit()
    
        print("\n批改任务处理完成")
        
        # 检查任务状态
        print("\n任务状态:")
        try:
            from celery.result import AsyncResult
            result = AsyncResult(correction.task_id, app=celery_app)
            print(f"作文ID={correction.essay_id}, 任务ID={correction.task_id}, 状态={result.state}")
        except Exception as e:
            print(f"作文ID={correction.essay_id}, 任务ID={correction.task_id}, 状态检查失败: {str(e)}")

if __name__ == "__main__":
    process_pending_corrections() 