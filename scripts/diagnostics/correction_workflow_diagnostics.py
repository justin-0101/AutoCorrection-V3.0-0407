#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.tasks.celery_app import celery_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_tasks_status():
    """检查Celery任务状态和作文状态"""
    app = create_app()
    with app.app_context():
        try:
            # 初始化Celery检查器
            inspection = celery_app.control.inspect()
            
            # 检查活跃任务
            active_tasks = inspection.active() or {}
            scheduled_tasks = inspection.scheduled() or {}
            reserved_tasks = inspection.reserved() or {}
            
            total_active = 0
            for worker, tasks in active_tasks.items():
                total_active += len(tasks)
                logger.info(f"Worker {worker} 有 {len(tasks)} 个活跃任务")
                for task in tasks:
                    logger.info(f"  - {task['id']}: {task['name']} (运行时间: {task.get('time_start')})")
            
            total_scheduled = 0
            for worker, tasks in scheduled_tasks.items():
                total_scheduled += len(tasks)
                logger.info(f"Worker {worker} 有 {len(tasks)} 个计划任务")
            
            total_reserved = 0
            for worker, tasks in reserved_tasks.items():
                total_reserved += len(tasks)
                logger.info(f"Worker {worker} 有 {len(tasks)} 个预留任务")
            
            logger.info(f"总计: {total_active} 个活跃任务, {total_scheduled} 个计划任务, {total_reserved} 个预留任务")
            
            # 检查数据库中的作文状态
            pending_essays = db.session.query(Essay).filter(Essay.status == EssayStatus.PENDING.value).all()
            correcting_essays = db.session.query(Essay).filter(Essay.status == EssayStatus.CORRECTING.value).all()
            failed_essays = db.session.query(Essay).filter(Essay.status == EssayStatus.FAILED.value).all()
            
            logger.info(f"数据库中有 {len(pending_essays)} 个等待批改的作文")
            logger.info(f"数据库中有 {len(correcting_essays)} 个正在批改的作文")
            logger.info(f"数据库中有 {len(failed_essays)} 个批改失败的作文")
            
            # 详细检查正在批改的作文
            if correcting_essays:
                logger.info("=== 正在批改的作文详情 ===")
                task_ids = []
                for essay in correcting_essays:
                    # 获取关联的批改记录
                    correction = db.session.query(Correction).filter(
                        Correction.essay_id == essay.id,
                        Correction.status == CorrectionStatus.CORRECTING.value
                    ).first()
                    
                    logger.info(f"作文ID: {essay.id}, 标题: {essay.title[:30]}...")
                    if correction:
                        logger.info(f"  关联的批改记录ID: {correction.id}")
                        logger.info(f"  批改任务ID: {correction.task_id}")
                        if correction.task_id:
                            task_ids.append(correction.task_id)
                    else:
                        logger.info(f"  没有找到关联的批改记录！")
                
                # 检查任务是否真的在Celery中运行
                all_active_ids = []
                for worker, tasks in active_tasks.items():
                    all_active_ids.extend([task['id'] for task in tasks])
                
                for task_id in task_ids:
                    if task_id in all_active_ids:
                        logger.info(f"任务ID {task_id} 正在Celery中运行")
                    else:
                        logger.warning(f"任务ID {task_id} 不在Celery活跃任务中，可能是任务已完成或失败但状态未更新")
            
            # 检查批改记录和作文状态是否一致
            inconsistent_count = 0
            corrections = db.session.query(Correction).all()
            logger.info("=== 检查批改记录和作文状态一致性 ===")
            
            for correction in corrections:
                essay = db.session.query(Essay).filter(Essay.id == correction.essay_id).first()
                if not essay:
                    logger.error(f"批改记录ID {correction.id} 关联的作文ID {correction.essay_id} 不存在")
                    continue
                
                if essay.status != correction.status:
                    inconsistent_count += 1
                    logger.warning(f"不一致: 作文ID {essay.id} 状态为 {essay.status}，但关联的批改记录状态为 {correction.status}")
            
            logger.info(f"发现 {inconsistent_count} 个状态不一致的记录")
            
        except Exception as e:
            logger.error(f"检查任务状态时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    check_tasks_status() 