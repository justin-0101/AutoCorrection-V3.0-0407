#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
维护任务模块
提供系统维护相关的任务，包括数据清理、任务状态管理等
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import SQLAlchemyError
from celery.result import AsyncResult

from app.models.db import db
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.models.task_status import TaskStatus, TaskState
from app.tasks.celery_app import celery_app

# 获取任务专用日志记录器
logger = get_task_logger('app.tasks.maintenance_tasks')

@celery_app.task(
    name='app.tasks.maintenance_tasks.cleanup_stale_task_statuses',
    bind=True,
    max_retries=2,
    acks_late=True,
    queue='periodic'
)
def cleanup_stale_task_statuses(self, days_to_keep=30, batch_size=1000):
    """
    清理长时间未完成的任务状态记录
    
    Args:
        self: Celery任务实例
        days_to_keep: 保留的天数，早于此天数的记录将被清理
        batch_size: 每批处理的记录数
        
    Returns:
        dict: 处理结果
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] 开始清理过时的任务状态记录，保留最近 {days_to_keep} 天的记录")
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # 记录开始的任务状态
    try:
        task_status = TaskStatus.create_from_task(
            task_id=task_id,
            task_name='cleanup_stale_task_statuses',
            args=f"[{days_to_keep}, {batch_size}]",
            worker_id=self.request.hostname
        )
        task_status.mark_as_started()
    except Exception as e:
        logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
    
    try:
        # 准备查询条件 - 清理以下任务状态:
        # 1. 早于截止日期的成功任务
        # 2. 早于截止日期的失败任务
        # 3. 早于截止日期的已拒绝任务
        # 4. 早于截止日期的已撤销任务
        # 5. 截止日期前开始但未更新状态的任务 (可能卡住)
        
        completed_states = [TaskState.SUCCESS, TaskState.FAILURE, TaskState.REJECTED, TaskState.REVOKED]
        
        # 1. 删除已完成的过期任务
        stale_tasks = TaskStatus.query.filter(
            TaskStatus.created_at < cutoff_date,
            TaskStatus.status.in_(completed_states)
        ).limit(batch_size).all()
        
        deleted_count = len(stale_tasks)
        
        for task in stale_tasks:
            db.session.delete(task)
        
        db.session.commit()
        logger.info(f"[{task_id}] 删除了 {deleted_count} 条已完成的过时任务记录")
        
        # 2. 处理卡住的任务（开始执行但长时间未更新）
        hanging_cutoff = datetime.utcnow() - timedelta(days=2)  # 2天未更新的任务视为卡住
        
        hanging_tasks = TaskStatus.query.filter(
            TaskStatus.created_at < hanging_cutoff,
            TaskStatus.status.in_([TaskState.STARTED, TaskState.PENDING, TaskState.RECEIVED, TaskState.RETRY])
        ).limit(batch_size).all()
        
        hanging_count = len(hanging_tasks)
        
        # 将卡住的任务标记为失败
        for task in hanging_tasks:
            task.mark_as_failure(error_message="任务执行时间过长，系统自动标记为失败")
        
        db.session.commit()
        logger.info(f"[{task_id}] 标记了 {hanging_count} 条卡住的任务为失败状态")
        
        # 更新任务状态
        result = {
            'status': 'success',
            'deleted_count': deleted_count,
            'hanging_tasks_marked': hanging_count,
            'cutoff_date': cutoff_date.isoformat(),
            'task_id': task_id
        }
        
        if 'task_status' in locals():
            task_status.mark_as_success(result=result)
            
        return result
        
    except Exception as e:
        logger.error(f"[{task_id}] 清理任务状态记录失败: {str(e)}")
        
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=str(e))
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"[{task_id}] 将在 300 秒后重试清理任务")
            self.retry(exc=e, countdown=300)
            
        return {
            'status': 'error',
            'message': str(e),
            'task_id': task_id
        }


@celery_app.task(
    name='app.tasks.maintenance_tasks.archive_old_task_statuses',
    bind=True,
    max_retries=2,
    acks_late=True,
    queue='periodic'
)
def archive_old_task_statuses(self, days_threshold=90, batch_size=1000):
    """
    归档旧的任务状态记录（将其移至归档表）
    
    Args:
        self: Celery任务实例
        days_threshold: 归档阈值，早于此天数的记录将被归档
        batch_size: 每批处理的记录数
        
    Returns:
        dict: 处理结果
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] 开始归档旧任务状态记录，阈值: {days_threshold} 天")
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
    
    # 记录任务状态
    try:
        task_status = TaskStatus.create_from_task(
            task_id=task_id,
            task_name='archive_old_task_statuses',
            args=f"[{days_threshold}, {batch_size}]",
            worker_id=self.request.hostname
        )
        task_status.mark_as_started()
    except Exception as e:
        logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
    
    try:
        # 执行归档SQL (需保证数据库中有task_status_archive表)
        # 注意：以下SQL是伪代码，实际使用时需根据数据库类型调整
        
        # 方法1: 使用原生SQL (性能更好)
        # sql = """
        # INSERT INTO task_status_archive 
        # SELECT * FROM task_status 
        # WHERE created_at < :cutoff_date 
        # LIMIT :batch_size
        # """
        # result = db.session.execute(sql, {'cutoff_date': cutoff_date, 'batch_size': batch_size})
        # inserted_count = result.rowcount
        
        # sql_delete = """
        # DELETE FROM task_status 
        # WHERE id IN (
        #     SELECT id FROM task_status 
        #     WHERE created_at < :cutoff_date 
        #     LIMIT :batch_size
        # )
        # """
        # delete_result = db.session.execute(sql_delete, {'cutoff_date': cutoff_date, 'batch_size': batch_size})
        # deleted_count = delete_result.rowcount
        
        # 方法2: 使用ORM (更安全但性能较差)
        # 实际应用场景中，可能需要创建任务状态归档模型，此处仅做示意
        logger.info(f"[{task_id}] 暂未实现实际归档功能，需先创建归档表结构")
        
        # 模拟归档
        archived_count = 0
        deleted_count = 0
        
        result = {
            'status': 'success',
            'archived_count': archived_count,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'task_id': task_id,
            'message': '归档功能需先创建归档表后才能启用'
        }
        
        if 'task_status' in locals():
            task_status.mark_as_success(result=result)
            
        return result
        
    except Exception as e:
        logger.error(f"[{task_id}] 归档任务状态记录失败: {str(e)}")
        
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=str(e))
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"[{task_id}] 将在 300 秒后重试归档任务")
            self.retry(exc=e, countdown=300)
            
        return {
            'status': 'error',
            'message': str(e),
            'task_id': task_id
        }

@celery_app.task(bind=True)
def check_and_fix_inconsistent_statuses(self):
    """
    检查并修复不一致的状态
    定期运行此任务以确保作文和批改记录的状态一致性
    
    Returns:
        Dict[str, Any]: 包含修复结果的字典
    """
    logger.info("开始执行状态一致性检查")
    
    try:
        # 1. 查找状态不一致的记录
        with db.session() as session:
            inconsistent_records = session.query(Essay, Correction).join(
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
                
                # 根据任务状态决定如何修复
                try:
                    session.begin_nested()
                    
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
                    
                    session.commit()
                    fixed_count += 1
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"修复作文 {essay.id} 状态失败: {str(e)}")
            
            # 3. 检查长时间处于CORRECTING状态的任务
            stale_time = datetime.now() - timedelta(hours=1)  # 1小时视为过期
            stale_corrections = session.query(Correction).filter(
                Correction.status == CorrectionStatus.CORRECTING,
                Correction.updated_at < stale_time
            ).all()
            
            logger.info(f"发现 {len(stale_corrections)} 条滞留的批改记录")
            stale_fixed_count = 0
            
            for correction in stale_corrections:
                essay = session.query(Essay).filter_by(id=correction.essay_id).first()
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
                    
                    try:
                        session.begin_nested()
                        
                        if task_status in ["PENDING", "STARTED", "RETRY"]:
                            # 任务仍在处理但时间过长，重置为待处理状态
                            logger.info(f"任务 {task_id} 运行时间过长，重置状态")
                            # 可选择终止任务
                            # task_result.revoke(terminate=True)
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
                            correction.error = "任务执行失败或被撤销"
                            logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为FAILED")
                        else:
                            # 未知状态，重置为待处理
                            essay.status = EssayStatus.PENDING
                            correction.status = CorrectionStatus.PENDING
                            correction.task_id = None
                            logger.info(f"未知任务状态，重置作文 {essay.id} 和批改 {correction.id} 的状态为PENDING")
                        
                        session.commit()
                        stale_fixed_count += 1
                    except SQLAlchemyError as e:
                        session.rollback()
                        logger.error(f"修复滞留任务 {task_id} 失败: {str(e)}")
                else:
                    # 没有任务ID，重置为待处理
                    try:
                        session.begin_nested()
                        essay.status = EssayStatus.PENDING
                        correction.status = CorrectionStatus.PENDING
                        logger.info(f"批改记录无任务ID，重置作文 {essay.id} 和批改 {correction.id} 的状态为PENDING")
                        session.commit()
                        stale_fixed_count += 1
                    except SQLAlchemyError as e:
                        session.rollback()
                        logger.error(f"重置无任务ID的批改记录 {correction.id} 失败: {str(e)}")
        
        return {
            "status": "success",
            "inconsistent_count": len(inconsistent_records),
            "fixed_count": fixed_count,
            "stale_count": len(stale_corrections),
            "stale_fixed_count": stale_fixed_count
        }
    except Exception as e:
        logger.exception(f"状态检查和修复过程出错: {str(e)}")
        return {"status": "error", "error": str(e)} 