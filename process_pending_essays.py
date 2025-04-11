#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
from datetime import datetime
from app import create_app
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction
from app.tasks.correction_tasks import process_essay_correction

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("process_pending")

def process_pending_essays():
    """处理所有待批改的作文"""
    app = create_app()
    
    with app.app_context():
        try:
            # 查找所有处于"pending"状态的作文
            pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING.value).all()
            
            if not pending_essays:
                logger.info("没有找到待批改的作文")
                return
            
            logger.info(f"找到 {len(pending_essays)} 篇待批改的作文")
            
            # 依次提交每个作文的批改任务
            for essay in pending_essays:
                logger.info(f"提交作文批改任务，ID:{essay.id}, 标题:{essay.title}")
                
                # 提交Celery任务
                task = process_essay_correction.delay(essay.id)
                
                logger.info(f"作文批改任务已提交，作文ID:{essay.id}, 任务ID:{task.id}")
            
            logger.info("所有待批改的作文都已提交到任务队列")
            
        except Exception as e:
            logger.error(f"处理待批改作文时发生错误: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("开始处理待批改作文...")
    process_pending_essays()
    logger.info("待批改作文处理完成") 