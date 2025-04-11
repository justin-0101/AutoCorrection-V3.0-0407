#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
from datetime import datetime
from app import create_app
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction
from app.models.db import db
from app.models.task_status import TaskStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("essay_status_fix")

def fix_essay_status():
    """修复处于'correcting'状态的作文，将其重置为'pending'状态"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找所有处于"correcting"状态的作文
            correcting_essays = Essay.query.filter_by(status=EssayStatus.CORRECTING.value).all()
            
            if not correcting_essays:
                logger.info("没有找到处于'correcting'状态的作文，无需修复")
                return
            
            logger.info(f"找到 {len(correcting_essays)} 篇处于'correcting'状态的作文")
            
            # 依次修复每个作文的状态
            for essay in correcting_essays:
                logger.info(f"正在修复作文 ID:{essay.id}, 标题:{essay.title}")
                
                # 查找关联的批改记录
                correction = Correction.query.filter_by(essay_id=essay.id).first()
                
                # 查找关联的任务状态
                tasks = TaskStatus.query.filter_by(
                    related_type='essay',
                    related_id=str(essay.id)
                ).all()
                
                # 1. 更新作文状态为'pending'
                essay.status = EssayStatus.PENDING.value
                essay.updated_at = datetime.now()
                
                # 2. 如果有批改记录，更新其状态
                if correction:
                    logger.info(f"  更新批改记录 ID:{correction.id}, 状态:{correction.status} -> pending")
                    correction.status = 'pending'
                
                # 3. 如果有相关任务记录，将其标记为失败
                if tasks:
                    for task in tasks:
                        if task.status in ['PENDING', 'STARTED']:
                            logger.info(f"  更新任务记录 ID:{task.task_id}, 状态:{task.status} -> FAILURE")
                            task.status = 'FAILURE'
                            task.completed_at = datetime.now()
                            task.error_message = '由系统管理员手动终止并重置'
                
                # 提交更改
                db.session.commit()
                logger.info(f"  作文 ID:{essay.id} 状态修复完成")
            
            logger.info("所有作文状态修复完成")
            
        except Exception as e:
            logger.error(f"修复作文状态时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
        finally:
            db.session.close()

if __name__ == "__main__":
    logger.info("开始修复作文状态...")
    fix_essay_status()
    logger.info("作文状态修复完成") 