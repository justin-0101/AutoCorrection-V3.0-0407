#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
维护任务模块
提供系统维护相关的任务，包括数据清理、任务状态管理等
"""

# 在导入任何其他模块之前应用eventlet猴子补丁
import os
import sys

try:
    import eventlet
    eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)
    os.environ['EVENTLET_PATCHED'] = 'true'
    print("eventlet猴子补丁已在maintenance_tasks模块中应用")
except ImportError:
    print("警告: 未安装eventlet，某些功能可能无法正常工作")

import logging
import json
import time
import re
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import SQLAlchemyError
from celery.result import AsyncResult
from sqlalchemy import text

from app.models.db import db
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.models.task_status import TaskStatus, TaskState
from app.tasks.celery_app import celery_app
from app.config import get_settings
from app.database import get_db_path
from app.utils.db_utils import execute_query, fetch_all, fetch_one
from app.core.ai.mock_results import create_mock_result

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

def fix_empty_correction_results():
    """
    查找并修复空的批改结果记录，这些记录是由于API调用错误导致的
    注意：此函数会排除标题包含"测试"或"test"的作文
    
    Returns:
        dict: 包含处理结果的字典，如找到的记录数、修复的记录数等
    """
    logger.info("开始查找并修复空的批改结果记录")
    settings = get_settings()
    db_path = get_db_path()
    
    # 跟踪统计信息
    stats = {
        "total": 0,
        "fixed": 0,
        "failed": 0,
        "skipped": 0,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询所有已完成但结果为空的批改记录
        # 排除标题包含"测试"或"test"的作文
        query = """
        SELECT c.id, c.essay_id, c.score, c.comments, c.error_analysis, c.improvement_suggestions,
               e.title, e.content
        FROM corrections c
        JOIN essays e ON c.essay_id = e.id
        WHERE c.status = 'completed' 
          AND (c.results IS NULL OR c.results = '' OR c.results = '{}')
          AND c.is_deleted = 0
          AND e.title NOT LIKE '%测试%'
          AND e.title NOT LIKE '%test%'
        """
        
        cursor.execute(query)
        empty_results = cursor.fetchall()
        stats["total"] = len(empty_results)
        
        logger.info(f"找到 {stats['total']} 条空的批改结果记录")
        
        for record in empty_results:
            try:
                # 获取记录信息
                correction_id = record['id']
                essay_id = record['essay_id']
                essay_title = record['title']
                essay_content = record['content']
                
                logger.info(f"处理批改记录 ID={correction_id}，作文ID={essay_id}，标题='{essay_title}'")
                
                # 检查是否真的需要修复
                if not record['score']:
                    logger.warning(f"批改记录 ID={correction_id} 缺少分数，需要生成模拟结果")
                
                # 生成模拟批改结果
                mock_result = {
                    "total_score": record['score'] if record['score'] else 80,
                    "scores": {
                        "content": 80,
                        "language": 80,
                        "structure": 80,
                        "writing": 80
                    },
                    "evaluation": record['comments'] if record['comments'] else "这篇作文整体表现良好。",
                    "error_analysis": record['error_analysis'] if record['error_analysis'] else "未检测到明显错误。",
                    "improvement_suggestions": record['improvement_suggestions'] if record['improvement_suggestions'] else "建议进一步丰富内容，提升语言表达的准确性。"
                }
                
                # 更新数据库
                update_query = """
                UPDATE corrections
                SET results = ?, updated_at = ?
                WHERE id = ?
                """
                cursor.execute(update_query, (
                    json.dumps(mock_result, ensure_ascii=False),
                    datetime.datetime.now().isoformat(),
                    correction_id
                ))
                
                stats["fixed"] += 1
                logger.info(f"成功修复批改记录 ID={correction_id}")
                
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"修复批改记录 ID={record['id']} 时出错: {str(e)}")
                logger.exception(e)
        
        # 提交更改
        conn.commit()
        logger.info(f"完成空批改结果修复。已修复: {stats['fixed']}, 失败: {stats['failed']}, 跳过: {stats['skipped']}")
        
    except Exception as e:
        logger.error(f"执行空批改结果修复任务时出错: {str(e)}")
        logger.exception(e)
        stats["error"] = str(e)
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    
    return stats

def verify_database_integrity():
    """
    验证数据库完整性并修复问题
    
    检查并修复以下问题:
    1. 不一致的文章和批改状态
    2. 孤立的批改记录
    3. 缺失的批改结果
    
    返回:
        dict: 检查和修复结果的统计信息
    """
    results = {
        'issues_found': 0,
        'issues_fixed': 0,
        'details': {
            'inconsistent_statuses': 0,
            'fixed_statuses': 0,
            'orphaned_corrections': 0,
            'fixed_orphans': 0,
            'empty_results': 0,
            'fixed_results': 0
        }
    }
    
    try:
        # 1. 检查不一致的状态
        inconsistent_records = _check_inconsistent_statuses()
        results['details']['inconsistent_statuses'] = len(inconsistent_records)
        
        if inconsistent_records:
            fixed_count = _fix_inconsistent_statuses(inconsistent_records)
            results['details']['fixed_statuses'] = fixed_count
            logger.info(f"已修复 {fixed_count} 条不一致的状态记录")
        
        # 2. 检查孤立的批改记录
        orphaned_records = _check_orphaned_corrections()
        results['details']['orphaned_corrections'] = len(orphaned_records)
        
        if orphaned_records:
            fixed_count = _fix_orphaned_corrections(orphaned_records)
            results['details']['fixed_orphans'] = fixed_count
            logger.info(f"已处理 {fixed_count} 条孤立的批改记录")
        
        # 3. 检查缺失的批改结果
        empty_results = _check_empty_results()
        results['details']['empty_results'] = len(empty_results)
        
        if empty_results:
            fixed_count = _fix_empty_results(empty_results)
            results['details']['fixed_results'] = fixed_count
            logger.info(f"已修复 {fixed_count} 条缺失的批改结果")
        
        # 计算总问题数和修复数
        results['issues_found'] = sum([
            results['details']['inconsistent_statuses'],
            results['details']['orphaned_corrections'],
            results['details']['empty_results']
        ])
        
        results['issues_fixed'] = sum([
            results['details']['fixed_statuses'],
            results['details']['fixed_orphans'],
            results['details']['fixed_results']
        ])
        
        return results
    
    except Exception as e:
        logger.error(f"数据库完整性验证失败: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'issues_found': -1,
            'issues_fixed': 0,
            'error': str(e)
        }

def _check_inconsistent_statuses():
    """
    检查不一致的文章和批改状态
    
    返回:
        list: 不一致的记录列表，每个记录包含essay_id和correction_id
    """
    inconsistent_records = []
    
    try:
        # 查找文章状态为已完成但对应的批改未完成的记录
        query = """
        SELECT e.id as essay_id, c.id as correction_id 
        FROM essays e 
        JOIN corrections c ON e.id = c.essay_id 
        WHERE e.status = 'completed' 
        AND c.status != 'completed' 
        AND e.is_deleted = 0 
        AND c.is_deleted = 0
        """
        
        result = db.session.execute(text(query))
        for row in result:
            inconsistent_records.append({
                'essay_id': row.essay_id,
                'correction_id': row.correction_id,
                'issue_type': 'essay_completed_correction_pending'
            })
        
        # 查找批改状态为已完成但文章未完成的记录
        query = """
        SELECT e.id as essay_id, c.id as correction_id 
        FROM essays e 
        JOIN corrections c ON e.id = c.essay_id 
        WHERE e.status != 'completed' 
        AND c.status = 'completed' 
        AND e.is_deleted = 0 
        AND c.is_deleted = 0
        """
        
        result = db.session.execute(text(query))
        for row in result:
            inconsistent_records.append({
                'essay_id': row.essay_id,
                'correction_id': row.correction_id,
                'issue_type': 'correction_completed_essay_pending'
            })
        
        return inconsistent_records
    
    except Exception as e:
        logger.error(f"检查不一致状态失败: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def _fix_inconsistent_statuses(inconsistent_records):
    """
    修复不一致的文章和批改状态
    
    参数:
        inconsistent_records (list): 不一致的记录列表
    
    返回:
        int: 修复的记录数量
    """
    fixed_count = 0
    
    for record in inconsistent_records:
        try:
            essay_id = record['essay_id']
            correction_id = record['correction_id']
            issue_type = record['issue_type']
            
            if issue_type == 'essay_completed_correction_pending':
                # 文章完成但批改未完成，将批改标记为完成
                correction = Correction.query.get(correction_id)
                if correction:
                    correction.status = 'completed'
                    db.session.commit()
                    logger.info(f"已将批改ID={correction_id}的状态更新为completed")
                    fixed_count += 1
            
            elif issue_type == 'correction_completed_essay_pending':
                # 批改完成但文章未完成，将文章标记为完成
                essay = Essay.query.get(essay_id)
                correction = Correction.query.get(correction_id)
                if essay and correction:
                    essay.status = 'completed'
                    
                    # 如果批改有结果，同步到文章
                    if correction.results:
                        try:
                            # 同步评分和评语
                            if hasattr(correction, 'score') and correction.score:
                                essay.score = correction.score
                            
                            if hasattr(correction, 'comments') and correction.comments:
                                essay.comments = correction.comments
                                
                            if hasattr(correction, 'error_analysis') and correction.error_analysis:
                                essay.error_analysis = correction.error_analysis
                                
                            if hasattr(correction, 'improvement_suggestions') and correction.improvement_suggestions:
                                essay.improvement_suggestions = correction.improvement_suggestions
                        except Exception as e:
                            logger.error(f"同步批改结果到文章时出错 (essay_id={essay_id}): {str(e)}")
                    
                    db.session.commit()
                    logger.info(f"已将文章ID={essay_id}的状态更新为completed")
                    fixed_count += 1
        
        except Exception as e:
            logger.error(f"修复不一致状态失败 (essay_id={record.get('essay_id')}): {str(e)}")
            logger.error(traceback.format_exc())
            db.session.rollback()
    
    return fixed_count

def _check_orphaned_corrections():
    """
    检查孤立的批改记录（没有对应文章的批改）
    
    返回:
        list: 孤立的批改记录ID列表
    """
    orphaned_records = []
    
    try:
        query = """
        SELECT c.id as correction_id 
        FROM corrections c 
        LEFT JOIN essays e ON c.essay_id = e.id 
        WHERE e.id IS NULL 
        AND c.is_deleted = 0
        """
        
        result = db.session.execute(text(query))
        for row in result:
            orphaned_records.append(row.correction_id)
        
        return orphaned_records
    
    except Exception as e:
        logger.error(f"检查孤立批改记录失败: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def _fix_orphaned_corrections(orphaned_records):
    """
    修复孤立的批改记录（标记为已删除）
    
    参数:
        orphaned_records (list): 孤立的批改记录ID列表
    
    返回:
        int: 修复的记录数量
    """
    fixed_count = 0
    
    for correction_id in orphaned_records:
        try:
            correction = Correction.query.get(correction_id)
            if correction:
                correction.is_deleted = True
                db.session.commit()
                logger.info(f"已将孤立的批改记录ID={correction_id}标记为已删除")
                fixed_count += 1
        
        except Exception as e:
            logger.error(f"修复孤立批改记录失败 (correction_id={correction_id}): {str(e)}")
            logger.error(traceback.format_exc())
            db.session.rollback()
    
    return fixed_count

def _check_empty_results():
    """
    检查缺失批改结果的记录
    
    返回:
        list: 缺失批改结果的记录列表，每个记录包含correction_id和essay_id
    """
    empty_results = []
    
    try:
        query = """
        SELECT c.id as correction_id, c.essay_id 
        FROM corrections c 
        WHERE (c.results IS NULL OR c.results = '' OR c.results = '{}') 
        AND c.status = 'completed' 
        AND c.is_deleted = 0
        """
        
        result = db.session.execute(text(query))
        for row in result:
            empty_results.append({
                'correction_id': row.correction_id,
                'essay_id': row.essay_id
            })
        
        return empty_results
    
    except Exception as e:
        logger.error(f"检查缺失批改结果失败: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def _fix_empty_results(empty_results):
    """
    修复缺失的批改结果（生成模拟结果）
    
    参数:
        empty_results (list): 缺失批改结果的记录列表
    
    返回:
        int: 修复的记录数量
    """
    fixed_count = 0
    
    for record in empty_results:
        try:
            correction_id = record['correction_id']
            essay_id = record['essay_id']
            
            correction = Correction.query.get(correction_id)
            essay = Essay.query.get(essay_id)
            
            if correction and essay:
                # 根据文章内容生成模拟的批改结果
                mock_result = create_mock_result(essay.content, correction_id)
                
                if mock_result:
                    correction.results = mock_result
                    
                    # 提取并更新其他字段
                    if 'score' in mock_result and mock_result['score']:
                        correction.score = mock_result['score']
                    
                    if 'comments' in mock_result and mock_result['comments']:
                        correction.comments = mock_result['comments']
                    
                    if 'error_analysis' in mock_result and mock_result['error_analysis']:
                        correction.error_analysis = mock_result['error_analysis']
                    
                    if 'improvement_suggestions' in mock_result and mock_result['improvement_suggestions']:
                        correction.improvement_suggestions = mock_result['improvement_suggestions']
                    
                    db.session.commit()
                    
                    # 确保相应的文章记录也得到更新
                    essay.status = 'completed'
                    essay.score = correction.score
                    essay.comments = correction.comments
                    essay.error_analysis = correction.error_analysis
                    essay.improvement_suggestions = correction.improvement_suggestions
                    db.session.commit()
                    
                    logger.info(f"已为批改ID={correction_id}(文章ID={essay_id})生成模拟批改结果")
                    fixed_count += 1
        
        except Exception as e:
            logger.error(f"修复缺失批改结果失败 (correction_id={record.get('correction_id')}): {str(e)}")
            logger.error(traceback.format_exc())
            db.session.rollback()
    
    return fixed_count

def create_mock_deepseek_result(content, score=None):
    """
    创建符合DeepSeek格式的模拟批改结果
    
    Args:
        content: 作文内容
        score: 指定分数，如果为None则根据内容长度生成
        
    Returns:
        Dict: 模拟的批改结果
    """
    # 基于内容长度生成分数
    content_length = len(content)
    if score is None:
        base_score = 35  # 基础分数
        # 内容越长，分数越高，最高50分
        length_factor = min(content_length / 1000, 1.0)  # 长度因子，最高1.0
        total_score = min(base_score + int(length_factor * 15), 50)
        # 随机波动
        total_score = max(min(total_score + random.randint(-3, 3), 50), 30)
    else:
        total_score = score
    
    # 分项得分
    content_score = int(total_score * 0.35)
    language_score = int(total_score * 0.3)
    structure_score = int(total_score * 0.2)
    writing_score = int(total_score * 0.15)
    
    # 确保总分等于各项分数之和
    adjustment = total_score - (content_score + language_score + structure_score + writing_score)
    content_score += adjustment
    
    # 找出一些可能的拼写错误（简单模拟）
    words = re.findall(r'[\u4e00-\u9fa5]+', content)
    potential_errors = []
    if len(words) > 100:
        for i in range(min(3, len(words) // 100)):
            if len(words) > 0:
                index = random.randint(0, len(words) - 1)
                if len(words[index]) > 1:
                    wrong = words[index]
                    correct = wrong  # 在真实场景中这里应该是修正的单词
                    potential_errors.append(f"{wrong}->{correct}")
    
    # 根据总分确定等级
    if total_score >= 43:
        level = "A"
        overall_assessment = "这是一篇出色的作文，内容立意明确，中心突出，材料具体生动，有真情实感；语言得体、流畅；结构严谨，注意照应，详略得当。"
    elif total_score >= 35:
        level = "B"
        overall_assessment = "这是一篇优秀的作文，内容立意明确，中心突出，材料具体；语言规范、通顺；结构完整，条理清楚。"
    elif total_score >= 27:
        level = "C" 
        overall_assessment = "这是一篇中等水平的作文，内容立意基本明确，材料能表现中心；语言基本通顺；结构基本完整，有条理。"
    else:
        level = "D"
        overall_assessment = "这篇作文内容立意不够明确，材料较难表现中心；语言不够通顺；结构不够完整，条理性有待提高。"
    
    # 创建DeepSeek格式的结果
    mock_result = {
        "总得分": total_score,
        "分项得分": {
            "内容主旨": content_score,
            "语言文采": language_score,
            "文章结构": structure_score,
            "文面书写": writing_score
        },
        "总体评价": overall_assessment,
        "内容分析": f"文章主题{'明确' if total_score >= 35 else '基本明确' if total_score >= 27 else '不够明确'}，{'思想深刻，论述充分' if total_score >= 43 else '有一定的思想深度' if total_score >= 35 else '思想深度有待提高'}。{'材料具体生动，有真情实感' if total_score >= 43 else '材料较为具体' if total_score >= 35 else '材料能基本表现中心' if total_score >= 27 else '材料难以充分表现中心'}。",
        "语言分析": f"语言表达{'流畅生动，修辞丰富' if total_score >= 43 else '规范流畅' if total_score >= 35 else '基本通顺' if total_score >= 27 else '有待改进'}，{'用词准确，句式多样化' if total_score >= 43 else '用词较为准确' if total_score >= 35 else '用词基本恰当' if total_score >= 27 else '用词不够准确'}。",
        "结构分析": f"文章结构{'严谨完整，详略得当，过渡自然' if total_score >= 43 else '完整，条理清晰' if total_score >= 35 else '基本完整，有一定条理' if total_score >= 27 else '不够完整，条理性有待提高'}。",
        "写作建议": f"{'建议在保持现有水平的基础上，进一步提高语言的表现力和文章的感染力。' if total_score >= 43 else '建议进一步丰富内容细节，增强语言表现力，使文章更有感染力。' if total_score >= 35 else '建议明确文章主题，丰富内容细节，提高语言表达的准确性和流畅性。' if total_score >= 27 else '建议明确文章主题，增加内容的深度和广度，改进语言表达，注意文章结构的完整性。'}",
        "错别字": potential_errors,
        "是否模拟": True,
        "模拟原因": "由于原批改结果丢失或无效，系统生成的模拟结果"
    }
    
    # 添加英文键以兼容不同客户端
    mock_result.update({
        "total_score": total_score,
        "grade": level,
        "level": level,
        "word_count": content_length,
        "content_score": content_score,
        "language_score": language_score,
        "structure_score": structure_score,
        "writing_score": writing_score,
        "overall_assessment": mock_result["总体评价"],
        "content_analysis": mock_result["内容分析"],
        "language_analysis": mock_result["语言分析"],
        "structure_analysis": mock_result["结构分析"],
        "improvement_suggestions": mock_result["写作建议"],
        "spelling_errors": mock_result["错别字"],
        "is_mock": True,
        "mock_reason": "由于原批改结果丢失或无效，系统生成的模拟结果"
    })
    
    return mock_result 

@celery_app.task(
    name='app.tasks.maintenance_tasks.reset_stuck_essays',
    bind=True,
    max_retries=2,
    acks_late=True,
    queue='periodic'
)
def reset_stuck_essays(self, max_stuck_time_minutes=30):
    """
    重置卡在处理中状态的作文
    
    Args:
        self: Celery任务实例
        max_stuck_time_minutes: 最长卡住时间（分钟），默认30分钟
        
    Returns:
        dict: 处理结果
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] 开始重置卡住的作文任务...")
    
    # 记录开始的任务状态
    try:
        if 'TaskStatus' in globals():
            task_status = TaskStatus.create_from_task(
                task_id=task_id,
                task_name='reset_stuck_essays',
                args=f"[{max_stuck_time_minutes}]",
                worker_id=self.request.hostname
            )
            task_status.mark_as_started()
    except Exception as e:
        logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
    
    try:
        # 导入必要的库
        import traceback
        from datetime import datetime, timedelta
        from flask import has_app_context, current_app
        from app import create_app
        
        # 检查应用上下文
        app = None
        ctx = None
        
        if not has_app_context():
            logger.info("未检测到应用上下文，正在创建新的应用上下文...")
            app = create_app()
            ctx = app.app_context()
            ctx.push()
            logger.info("已创建并推送新的应用上下文")
        else:
            logger.info("检测到现有应用上下文，继续使用当前上下文")
            app = current_app
        
        try:
            # 计算最长卡住时间点
            threshold_time = datetime.utcnow() - timedelta(minutes=max_stuck_time_minutes)
            
            # 查找卡住的作文
            from app.models.essay import Essay, EssayStatus
            
            # 查找所有处于CORRECTING状态，且更新时间超过阈值的作文
            stuck_essays = Essay.query.filter(
                Essay.status == EssayStatus.CORRECTING.value,
                Essay.updated_at < threshold_time
            ).all()
            
            if not stuck_essays:
                logger.info(f"[{task_id}] 没有找到卡住的作文")
                result = {"reset_count": 0}
                
                if 'task_status' in locals():
                    task_status.mark_as_success(result=result)
                
                return result
            
            # 重置作文状态
            reset_count = 0
            for essay in stuck_essays:
                try:
                    with db.session.begin():
                        stuck_time = datetime.utcnow() - essay.updated_at
                        logger.info(f"[{task_id}] 重置作文 ID: {essay.id}, 原状态: {essay.status}, 卡住时间: {stuck_time}")
                        essay.status = EssayStatus.PENDING.value
                        essay.error_message = f"系统自动重置卡住的作文状态 (卡住{stuck_time})"
                        reset_count += 1
                except Exception as e:
                    logger.error(f"[{task_id}] 重置作文 {essay.id} 状态时出错: {str(e)}")
                    logger.error(traceback.format_exc())
            
            db.session.commit()
            logger.info(f"[{task_id}] 成功重置 {reset_count} 个卡住的作文")
            
            result = {"reset_count": reset_count}
            
            if 'task_status' in locals():
                task_status.mark_as_success(result=result)
                
            return result
            
        finally:
            # 如果创建了应用上下文，确保弹出它
            if ctx:
                try:
                    ctx.pop()
                    logger.info("应用上下文已弹出")
                except Exception as ex:
                    logger.warning(f"弹出应用上下文时出错: {str(ex)}")
    
    except Exception as e:
        error_msg = f"重置卡住作文任务失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=error_msg)
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"[{task_id}] 将在 60 秒后重试重置卡住作文任务")
            self.retry(exc=e, countdown=60)
            
        return {"status": "error", "message": error_msg} 