#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
状态一致性检查和修复工具
用于检查和修复作文状态与批改记录状态的不一致问题
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# 确保系统路径正确
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.extensions import db
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def fix_inconsistent_statuses(dry_run=True):
    """检查并修复不一致的状态
    
    Args:
        dry_run: 如果为True，只检查不修改
    
    Returns:
        dict: 包含修复结果的字典
    """
    try:
        app = create_app()
        with app.app_context():
            # 1. 查找状态不一致的记录
            inconsistent_records = db.session.query(Essay, Correction).join(
                Correction, Essay.id == Correction.essay_id
            ).filter(
                ((Essay.status == EssayStatus.CORRECTING) & 
                 (Correction.status != CorrectionStatus.CORRECTING)) |
                ((Essay.status != EssayStatus.CORRECTING) & 
                 (Correction.status == CorrectionStatus.CORRECTING))
            ).all()
            
            logger.info(f"发现 {len(inconsistent_records)} 条状态不一致的记录")
            fixed_count = 0
            
            # 2. 修复不一致状态
            for essay, correction in inconsistent_records:
                logger.info(f"作文 {essay.id} 状态不一致: 作文状态={essay.status}, 批改状态={correction.status}")
                
                # 检查任务状态
                task_id = correction.task_id
                task_status = "UNKNOWN"
                if task_id:
                    task_result = AsyncResult(task_id, app=celery_app)
                    task_status = task_result.state
                    logger.info(f"任务 {task_id} 的状态为: {task_status}")
                else:
                    logger.warning(f"批改记录 {correction.id} 没有关联的任务ID")
                
                if not dry_run:
                    with db.session.begin():
                        # 根据任务状态决定如何修复
                        if task_status in ["PENDING", "STARTED", "RETRY"]:
                            # 任务正在处理，保持CORRECTING状态
                            essay.status = EssayStatus.CORRECTING
                            correction.status = CorrectionStatus.CORRECTING
                            logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为CORRECTING")
                        elif task_status in ["SUCCESS"]:
                            # 任务已成功，但状态未更新
                            essay.status = EssayStatus.COMPLETED
                            correction.status = CorrectionStatus.COMPLETED
                            logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为COMPLETED")
                        elif task_status in ["FAILURE", "REVOKED"]:
                            # 任务已失败
                            essay.status = EssayStatus.FAILED
                            correction.status = CorrectionStatus.FAILED
                            logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为FAILED")
                        else:
                            # 任务状态未知或不存在，重置为待处理
                            essay.status = EssayStatus.PENDING
                            correction.status = CorrectionStatus.PENDING
                            correction.task_id = None
                            logger.info(f"重置作文 {essay.id} 和批改 {correction.id} 的状态为PENDING")
                        fixed_count += 1
            
            # 3. 检查长时间处于CORRECTING状态的任务
            stale_time = datetime.utcnow() - timedelta(hours=1)  # 1小时视为过期
            stale_corrections = Correction.query.filter(
                Correction.status == CorrectionStatus.CORRECTING,
                Correction.updated_at < stale_time
            ).all()
            
            logger.info(f"发现 {len(stale_corrections)} 条滞留的批改记录")
            stale_fixed_count = 0
            
            for correction in stale_corrections:
                essay = Essay.query.get(correction.essay_id)
                if not essay:
                    logger.warning(f"批改记录 {correction.id} 的作文 {correction.essay_id} 不存在")
                    continue
                    
                logger.info(f"滞留的批改 {correction.id} (作文ID: {correction.essay_id}), "
                           f"更新时间: {correction.updated_at}")
                
                # 检查任务状态
                task_id = correction.task_id
                if task_id:
                    task_result = AsyncResult(task_id, app=celery_app)
                    task_status = task_result.state
                    logger.info(f"任务 {task_id} 的状态为: {task_status}")
                    
                    if not dry_run:
                        with db.session.begin():
                            if task_status in ["PENDING", "STARTED", "RETRY"]:
                                # 任务仍在处理但时间过长，重置为待处理状态
                                logger.info(f"任务 {task_id} 运行时间过长，重置状态")
                                essay.status = EssayStatus.PENDING
                                correction.status = CorrectionStatus.PENDING
                                correction.task_id = None
                            elif task_status in ["SUCCESS"]:
                                # 任务已成功但状态未更新
                                essay.status = EssayStatus.COMPLETED
                                correction.status = CorrectionStatus.COMPLETED
                                logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为COMPLETED")
                            elif task_status in ["FAILURE", "REVOKED"]:
                                # 任务已失败
                                essay.status = EssayStatus.FAILED
                                correction.status = CorrectionStatus.FAILED
                                correction.error_message = "任务执行失败或被撤销"
                                logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为FAILED")
                            else:
                                # 未知状态，重置为待处理
                                essay.status = EssayStatus.PENDING
                                correction.status = CorrectionStatus.PENDING
                                correction.task_id = None
                                logger.info(f"未知任务状态，重置作文 {essay.id} 和批改 {correction.id} 的状态为PENDING")
                            stale_fixed_count += 1
                else:
                    # 没有任务ID，重置为待处理
                    if not dry_run:
                        with db.session.begin():
                            essay.status = EssayStatus.PENDING
                            correction.status = CorrectionStatus.PENDING
                            logger.info(f"批改记录无任务ID，重置作文 {essay.id} 和批改 {correction.id} 的状态为PENDING")
                            stale_fixed_count += 1
            
            return {
                "inconsistent_count": len(inconsistent_records),
                "fixed_count": fixed_count,
                "stale_count": len(stale_corrections),
                "stale_fixed_count": stale_fixed_count,
                "dry_run": dry_run
            }
    except Exception as e:
        logger.exception(f"状态检查和修复过程出错: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # 检查命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='状态一致性检查和修复工具')
    parser.add_argument('--apply', action='store_true', help='应用修复（默认为干运行模式）')
    args = parser.parse_args()
    
    # 执行修复
    dry_run = not args.apply
    mode = "干运行模式" if dry_run else "修复模式"
    logger.info(f"开始状态一致性检查和修复 ({mode})")
    
    result = fix_inconsistent_statuses(dry_run=dry_run)
    
    logger.info(f"状态检查完成: 发现 {result['inconsistent_count']} 条不一致状态, "
               f"修复了 {result['fixed_count']} 条")
    logger.info(f"滞留任务检查: 发现 {result['stale_count']} 条滞留任务, "
               f"处理了 {result['stale_fixed_count']} 条")
    
    if dry_run and (result['inconsistent_count'] > 0 or result['stale_count'] > 0):
        logger.info("发现需要修复的问题，请使用 --apply 参数运行脚本以应用修复") 