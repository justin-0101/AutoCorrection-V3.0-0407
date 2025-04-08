#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量处理任务模块
提供高效的批量数据处理功能，优化大数据集处理性能
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

from app.tasks.celery_app import celery_app
from app.tasks.batch_optimization import (
    batch_processor, 
    iterate_in_chunks, 
    chunked_insert,
    monitor_performance,
    prioritize_task,
    with_thread_session
)
from app.tasks.logging_config import get_task_logger
from app.models.db import db
from app.models.essay import Essay
from app.models.user import User
from app.models.correction import Correction
from app.models.task_status import TaskStatus, TaskState

# 获取任务专用日志记录器
logger = get_task_logger()

def calculate_priority_by_essay_count(essay_ids=None, **kwargs):
    """
    根据作文数量计算优先级
    
    Args:
        essay_ids: 要处理的作文ID列表
        
    Returns:
        int: 优先级值(1-10)
    """
    if not essay_ids:
        return 5  # 默认中等优先级
    
    count = len(essay_ids)
    
    # 数量越多，优先级越低，避免阻塞系统
    if count > 500:
        return 2
    elif count > 200:
        return 3
    elif count > 100:
        return 4
    elif count > 50:
        return 5
    elif count > 20:
        return 6
    elif count > 10:
        return 7
    else:
        return 8  # 少量作文优先处理


@celery_app.task(
    name='app.tasks.batch_processor_tasks.bulk_update_essay_status',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    soft_time_limit=1800,  # 30分钟超时
    time_limit=2100        # 35分钟硬超时
)
@prioritize_task(calculate_priority_by_essay_count)
@monitor_performance(name="bulk_update_essay_status")
def bulk_update_essay_status(
    self, 
    essay_ids: List[int], 
    status: str,
    notify_users: bool = False,
    batch_size: int = 100,
    max_workers: int = 4
) -> Dict[str, Any]:
    """
    批量更新作文状态
    
    Args:
        self: Celery任务实例
        essay_ids: 作文ID列表
        status: 目标状态
        notify_users: 是否通知用户
        batch_size: 批量处理的尺寸
        max_workers: 最大工作线程数
        
    Returns:
        Dict: 处理结果
    """
    start_time = time.time()
    logger.info(f"开始批量更新 {len(essay_ids)} 个作文的状态为 '{status}'")
    
    try:
        # 记录任务状态
        try:
            task_status = TaskStatus.create_from_task(
                task_id=self.request.id,
                task_name='bulk_update_essay_status',
                args=f"[{len(essay_ids)} essays, status={status}]",
                worker_id=self.request.hostname
            )
            task_status.mark_as_started()
        except Exception as e:
            logger.warning(f"记录任务状态失败: {str(e)}")
        
        # 定义单个作文处理函数
        @with_thread_session
        def update_essay_status(session, essay_id):
            essay = session.query(Essay).get(essay_id)
            if not essay:
                return {
                    "essay_id": essay_id,
                    "status": "error",
                    "message": "作文不存在"
                }
            
            # 更新状态
            previous_status = essay.status
            essay.status = status
            essay.updated_at = datetime.now().timestamp()
            
            # 添加状态变更记录
            from app.models.essay_status_history import EssayStatusHistory
            status_history = EssayStatusHistory(
                essay_id=essay_id,
                previous_status=previous_status,
                new_status=status,
                changed_by='system',
                reason=f'批量状态更新任务 {self.request.id}'
            )
            session.add(status_history)
            
            # 提交更改
            try:
                session.commit()
                logger.debug(f"已更新作文 {essay_id} 状态: {previous_status} -> {status}")
                
                # 如果需要通知用户
                if notify_users and essay.user_id:
                    try:
                        from app.tasks.notification_tasks import send_task_failure_notification
                        send_task_failure_notification.delay(
                            task_id=self.request.id,
                            related_type='essay',
                            related_id=essay_id,
                            error_message=f"作文状态已更新: {previous_status} -> {status}"
                        )
                    except Exception as notify_error:
                        logger.error(f"通知用户失败 {essay.user_id}: {str(notify_error)}")
                
                return {
                    "essay_id": essay_id,
                    "status": "success",
                    "previous_status": previous_status,
                    "new_status": status
                }
            except Exception as commit_error:
                session.rollback()
                logger.error(f"更新作文 {essay_id} 状态失败: {str(commit_error)}")
                return {
                    "essay_id": essay_id,
                    "status": "error",
                    "message": str(commit_error)
                }
        
        # 错误处理函数
        def handle_error(essay_id, error):
            logger.error(f"处理作文 {essay_id} 时发生错误: {str(error)}")
            # 可以在这里添加额外的错误处理逻辑
        
        # 使用批处理器执行更新
        result = batch_processor(
            items=essay_ids,
            process_func=update_essay_status,
            batch_size=batch_size,
            max_workers=max_workers,
            use_threading=True,
            error_handler=handle_error
        )
        
        # 更新任务状态
        if 'task_status' in locals():
            if result['status'] == 'success':
                task_status.mark_as_success(result=result)
            elif result['status'] == 'partial_success':
                task_status.mark_as_success(
                    result=result,
                    warning_message=f"部分作文更新失败: {result['failed']}/{result['total']}"
                )
            else:
                task_status.mark_as_failure(
                    error_message=f"批量更新作文状态失败: {result['failed']}/{result['total']}"
                )
        
        return result
        
    except Exception as e:
        logger.error(f"批量更新作文状态任务异常: {str(e)}", exc_info=True)
        
        # 更新任务状态
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=str(e))
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 {self.default_retry_delay} 秒后重试批量更新作文状态")
            self.retry(exc=e, countdown=self.default_retry_delay)
        
        return {
            "status": "error",
            "message": f"批量更新作文状态任务异常: {str(e)}",
            "total": len(essay_ids),
            "processing_time": time.time() - start_time
        }


@celery_app.task(
    name='app.tasks.batch_processor_tasks.reprocess_failed_corrections',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    soft_time_limit=1800,  # 30分钟超时
    time_limit=2100        # 35分钟硬超时
)
@monitor_performance(name="reprocess_failed_corrections")
def reprocess_failed_corrections(
    self, 
    time_range_days: int = 7,
    max_essays: int = 500,
    batch_size: int = 50,
    high_priority: bool = False
) -> Dict[str, Any]:
    """
    重新处理失败的作文批改任务
    
    Args:
        self: Celery任务实例
        time_range_days: 查找多少天内的失败作文
        max_essays: 最大处理作文数量
        batch_size: 每批提交的作文数量
        high_priority: 是否以高优先级提交
        
    Returns:
        Dict: 处理结果
    """
    start_time = time.time()
    logger.info(f"开始查找并重新处理 {time_range_days} 天内的失败作文批改任务")
    
    try:
        # 记录任务状态
        try:
            task_status = TaskStatus.create_from_task(
                task_id=self.request.id,
                task_name='reprocess_failed_corrections',
                args=f"[days={time_range_days}, max={max_essays}, high_priority={high_priority}]",
                worker_id=self.request.hostname
            )
            task_status.mark_as_started()
        except Exception as e:
            logger.warning(f"记录任务状态失败: {str(e)}")
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range_days)
        
        # 转换为时间戳
        start_timestamp = start_date.timestamp()
        end_timestamp = end_date.timestamp()
        
        # 查询失败的作文
        with db.session() as session:
            failed_essays = session.query(Essay).filter(
                Essay.status == 'failed',
                Essay.created_at.between(start_timestamp, end_timestamp)
            ).limit(max_essays).all()
            
            logger.info(f"找到 {len(failed_essays)} 个失败的作文")
            
            if not failed_essays:
                result = {
                    "status": "success",
                    "message": f"未找到需要重新处理的失败作文",
                    "total": 0,
                    "processing_time": time.time() - start_time
                }
                
                if 'task_status' in locals():
                    task_status.mark_as_success(result=result)
                
                return result
            
            # 获取作文ID
            essay_ids = [essay.id for essay in failed_essays]
            
            # 分批重新提交作文批改任务
            from app.tasks.correction_tasks import batch_process_essays
            
            total_batches = (len(essay_ids) + batch_size - 1) // batch_size
            submitted_batches = 0
            batch_results = []
            
            for i in range(0, len(essay_ids), batch_size):
                batch = essay_ids[i:i+batch_size]
                
                try:
                    # 将作文状态更新为待处理
                    for essay_id in batch:
                        essay = session.query(Essay).get(essay_id)
                        if essay:
                            essay.status = 'pending'
                    session.commit()
                    
                    # 提交批处理任务
                    batch_task = batch_process_essays.delay(batch, high_priority)
                    
                    batch_results.append({
                        "batch": i // batch_size + 1,
                        "essay_count": len(batch),
                        "task_id": batch_task.id,
                        "status": "submitted"
                    })
                    
                    submitted_batches += 1
                    logger.info(f"已提交批次 {submitted_batches}/{total_batches}, "
                               f"包含 {len(batch)} 个作文, 任务ID: {batch_task.id}")
                    
                except Exception as batch_error:
                    logger.error(f"提交批次 {i // batch_size + 1} 失败: {str(batch_error)}")
                    batch_results.append({
                        "batch": i // batch_size + 1,
                        "essay_count": len(batch),
                        "status": "error",
                        "message": str(batch_error)
                    })
            
            result = {
                "status": "success" if submitted_batches == total_batches else "partial_success",
                "message": f"已提交 {submitted_batches}/{total_batches} 批作文重新批改",
                "total_essays": len(essay_ids),
                "submitted_batches": submitted_batches,
                "total_batches": total_batches,
                "batch_results": batch_results,
                "processing_time": time.time() - start_time
            }
            
            # 更新任务状态
            if 'task_status' in locals():
                if result['status'] == 'success':
                    task_status.mark_as_success(result=result)
                else:
                    task_status.mark_as_success(
                        result=result,
                        warning_message=f"部分批次提交失败: {total_batches - submitted_batches}/{total_batches}"
                    )
            
            return result
            
    except Exception as e:
        logger.error(f"重新处理失败作文任务异常: {str(e)}", exc_info=True)
        
        # 更新任务状态
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=str(e))
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 {self.default_retry_delay} 秒后重试重新处理失败作文任务")
            self.retry(exc=e, countdown=self.default_retry_delay)
        
        return {
            "status": "error",
            "message": f"重新处理失败作文任务异常: {str(e)}",
            "processing_time": time.time() - start_time
        }


@celery_app.task(
    name='app.tasks.batch_processor_tasks.bulk_delete_old_data',
    bind=True,
    max_retries=2,
    acks_late=True,
    soft_time_limit=1800,
    time_limit=2100
)
@monitor_performance(name="bulk_delete_old_data")
def bulk_delete_old_data(
    self, 
    data_type: str,
    days_to_keep: int = 90,
    batch_size: int = 1000,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    批量删除老数据，支持多种数据类型
    
    Args:
        self: Celery任务实例
        data_type: 数据类型，支持 'task_status', 'corrections', 'user_activity'
        days_to_keep: 保留多少天的数据
        batch_size: 每批处理的记录数
        dry_run: 是否只模拟执行不实际删除
        
    Returns:
        Dict: 处理结果
    """
    start_time = time.time()
    logger.info(f"开始批量删除 {data_type} 类型的老数据，保留最近 {days_to_keep} 天")
    
    try:
        # 记录任务状态
        try:
            task_status = TaskStatus.create_from_task(
                task_id=self.request.id,
                task_name='bulk_delete_old_data',
                args=f"[type={data_type}, days={days_to_keep}, dry_run={dry_run}]",
                worker_id=self.request.hostname
            )
            task_status.mark_as_started()
        except Exception as e:
            logger.warning(f"记录任务状态失败: {str(e)}")
        
        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_timestamp = cutoff_date.timestamp()
        
        # 获取要使用的模型和查询条件
        if data_type == 'task_status':
            from app.models.task_status import TaskStatus
            model = TaskStatus
            condition = TaskStatus.created_at < cutoff_timestamp
            id_column = TaskStatus.id
            date_column = TaskStatus.created_at
        elif data_type == 'corrections':
            from app.models.correction import Correction
            model = Correction
            condition = Correction.created_at < cutoff_timestamp
            id_column = Correction.id
            date_column = Correction.created_at
        elif data_type == 'user_activity':
            from app.models.user_activity import UserActivity
            model = UserActivity
            condition = UserActivity.created_at < cutoff_timestamp
            id_column = UserActivity.id
            date_column = UserActivity.created_at
        else:
            error_msg = f"不支持的数据类型: {data_type}"
            logger.error(error_msg)
            
            if 'task_status' in locals():
                task_status.mark_as_failure(error_message=error_msg)
                
            return {
                "status": "error",
                "message": error_msg,
                "processing_time": time.time() - start_time
            }
        
        with db.session() as session:
            # 统计要删除的记录总数
            total_records = session.query(id_column).filter(condition).count()
            logger.info(f"找到 {total_records} 条要删除的 {data_type} 记录")
            
            if total_records == 0:
                result = {
                    "status": "success",
                    "message": f"没有找到需要删除的 {data_type} 记录",
                    "total": 0,
                    "deleted": 0,
                    "dry_run": dry_run,
                    "cutoff_date": cutoff_date.isoformat(),
                    "processing_time": time.time() - start_time
                }
                
                if 'task_status' in locals():
                    task_status.mark_as_success(result=result)
                
                return result
            
            # 如果是干运行模式，只返回统计信息
            if dry_run:
                # 获取最早和最晚的记录日期
                oldest_record = session.query(db.func.min(date_column)).filter(condition).scalar()
                newest_record = session.query(db.func.max(date_column)).filter(condition).scalar()
                
                oldest_date = datetime.fromtimestamp(oldest_record) if oldest_record else None
                newest_date = datetime.fromtimestamp(newest_record) if newest_record else None
                
                result = {
                    "status": "success",
                    "message": f"找到 {total_records} 条要删除的 {data_type} 记录，干运行模式未执行删除",
                    "total": total_records,
                    "deleted": 0,
                    "dry_run": True,
                    "cutoff_date": cutoff_date.isoformat(),
                    "oldest_record_date": oldest_date.isoformat() if oldest_date else None,
                    "newest_record_date": newest_date.isoformat() if newest_date else None,
                    "processing_time": time.time() - start_time
                }
                
                if 'task_status' in locals():
                    task_status.mark_as_success(result=result)
                
                return result
            
            # 实际执行删除操作
            deleted_count = 0
            error_count = 0
            
            # 分批处理删除
            while True:
                # 获取一批要删除的记录ID
                batch_ids = session.query(id_column).filter(condition).limit(batch_size).all()
                if not batch_ids:
                    break
                
                # 将ID列表转换为纯整数列表
                batch_ids = [id_tuple[0] for id_tuple in batch_ids]
                
                try:
                    # 执行批量删除
                    delete_count = session.query(model).filter(
                        id_column.in_(batch_ids)
                    ).delete(synchronize_session=False)
                    
                    session.commit()
                    deleted_count += delete_count
                    logger.info(f"已删除 {deleted_count}/{total_records} 条 {data_type} 记录")
                    
                except Exception as batch_error:
                    session.rollback()
                    error_count += len(batch_ids)
                    logger.error(f"删除 {data_type} 批次数据时出错: {str(batch_error)}")
            
            result = {
                "status": "success" if error_count == 0 else "partial_success",
                "message": f"已删除 {deleted_count}/{total_records} 条 {data_type} 记录",
                "total": total_records,
                "deleted": deleted_count,
                "failed": error_count,
                "dry_run": False,
                "cutoff_date": cutoff_date.isoformat(),
                "processing_time": time.time() - start_time
            }
            
            # 更新任务状态
            if 'task_status' in locals():
                if result['status'] == 'success':
                    task_status.mark_as_success(result=result)
                else:
                    task_status.mark_as_success(
                        result=result,
                        warning_message=f"部分记录删除失败: {error_count}/{total_records}"
                    )
            
            return result
            
    except Exception as e:
        logger.error(f"批量删除 {data_type} 老数据任务异常: {str(e)}", exc_info=True)
        
        # 更新任务状态
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=str(e))
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 120 秒后重试批量删除老数据任务")
            self.retry(exc=e, countdown=120)
        
        return {
            "status": "error",
            "message": f"批量删除 {data_type} 老数据任务异常: {str(e)}",
            "processing_time": time.time() - start_time
        } 