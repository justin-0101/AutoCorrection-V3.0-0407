#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改相关的异步任务模块
用于定义各种作文批改的Celery任务，包括处理单个作文的批改、批量处理作文等
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError
from celery.exceptions import Retry
from celery import shared_task
# 重新组织导入语句，避免循环导入
from app.core.celery_app import celery
from app.core.db.transaction_utils import essay_update_transaction, correction_update_transaction
from app.models.db import db
from app.utils.exceptions import (
    AIServiceError, AIServiceRequestError, AIServiceLimitError,
    ResourceNotFoundError, ProcessingError, ConcurrentUpdateError
)
from celery.utils.log import get_task_logger
from flask import current_app
import traceback
from celery import Task as BaseTask
from app.core.ai.deepseek_client import DeepseekClient

# 延迟导入模型，避免循环导入
# app.core.essay.essay_service 和 app.core.correction.correction_service 也需要避免循环导入

# 创建任务专用的日志记录器
logger = get_task_logger(__name__)

def validate_essay_id(essay_id: int) -> bool:
    """
    验证作文ID是否有效
    
    Args:
        essay_id: 作文ID
        
    Returns:
        bool: 是否有效
    """
    if not essay_id or not isinstance(essay_id, int) or essay_id <= 0:
        logger.error(f"无效的作文ID: {essay_id}")
        return False
    return True


@celery.task(base=BaseTask)
def process_essay_correction(essay_id: int) -> Dict[str, Any]:
    """
    处理作文批改任务，使用乐观锁进行状态更新并设置事务超时
    
    Args:
        essay_id: 作文ID
        
    Returns:
        Dict: 处理结果
    """
    logger.info(f"开始处理作文批改任务 [essay_id={essay_id}]")
    
    try:
        # 延迟导入模型，避免循环导入
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        
        # 第一阶段：使用乐观锁和事务超时更新状态
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 在事务超时上下文中执行
                with essay_update_transaction(db.session, 3):  # 设置3秒超时
                    essay = Essay.query.get(essay_id)
                    if not essay:
                        raise ResourceNotFoundError(f"作文不存在 [id={essay_id}]")
                        
                    # 更新作文状态
                    essay_updated = essay.optimistic_update(
                        status=EssayStatus.PROCESSING.value,
                        updated_at=datetime.utcnow()
                    )
                
                with correction_update_transaction(db.session, 3):  # 设置3秒超时
                    correction = Correction.query.filter_by(essay_id=essay_id).first()
                    if not correction:
                        raise ResourceNotFoundError(f"批改记录不存在 [essay_id={essay_id}]")
                    
                    # 更新批改记录状态
                    correction_updated = correction.optimistic_update(
                        status=CorrectionStatus.PROCESSING.value,
                        updated_at=datetime.utcnow()
                    )
                
                if essay_updated and correction_updated:
                    break
                    
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.5)  # 短暂延迟后重试
                    continue
                    
                raise ConcurrentUpdateError("状态更新失败，已达到最大重试次数")
                
            except ConcurrentUpdateError as e:
                if retry_count >= max_retries - 1:
                    raise
                continue
        
        # 第二阶段：执行AI批改（无事务）
        try:
            ai_client = DeepseekClient()
            correction_result = ai_client.correct_essay(essay.content)
            
            if correction_result['status'] != 'success':
                raise ProcessingError(f"AI批改失败: {correction_result.get('message', '未知错误')}")
                
            result_data = correction_result['result']
            
        except Exception as e:
            logger.error(f"AI批改过程出错 [essay_id={essay_id}]: {str(e)}")
            # 使用乐观锁和事务超时更新失败状态
            retry_count = 0
            while retry_count < max_retries:
                try:
                    with essay_update_transaction(db.session, 3):
                        essay.optimistic_update(
                            status=EssayStatus.FAILED.value,
                            updated_at=datetime.utcnow()
                        )
                    
                    with correction_update_transaction(db.session, 3):
                        correction.optimistic_update(
                            status=CorrectionStatus.FAILED.value,
                            error_message=str(e),
                            updated_at=datetime.utcnow()
                        )
                    break
                except (ConcurrentUpdateError, SQLAlchemyError) as update_error:
                    logger.warning(f"更新失败状态时出错: {str(update_error)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(0.5)
                        continue
            raise ProcessingError(f"AI批改失败: {str(e)}")
        
        # 第三阶段：使用乐观锁和事务超时更新结果
        retry_count = 0
        while retry_count < max_retries:
            try:
                with correction_update_transaction(db.session, 5):  # 设置5秒超时（结果更新可能较大）
                    # 更新批改记录
                    correction_updated = correction.optimistic_update(
                        results=result_data,
                        score=result_data.get('total_score'),
                        content=result_data.get('corrected_content', ''),
                        comments=result_data.get('overall_assessment', ''),
                        error_analysis=result_data.get('spelling_errors', {}),
                        improvement_suggestions=result_data.get('improvement_suggestions', ''),
                        status=CorrectionStatus.COMPLETED.value,
                        completed_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                
                with essay_update_transaction(db.session, 5):  # 设置5秒超时
                    # 更新作文
                    essay_updated = essay.optimistic_update(
                        status=EssayStatus.COMPLETED.value,
                        score=result_data.get('total_score'),
                        corrected_content=result_data.get('corrected_content', ''),
                        comments=result_data.get('overall_assessment', ''),
                        error_analysis=result_data.get('spelling_errors', {}),
                        improvement_suggestions=result_data.get('improvement_suggestions', ''),
                        corrected_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                
                if correction_updated and essay_updated:
                    break
                    
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.5)
                    continue
                    
                raise ConcurrentUpdateError("结果更新失败，已达到最大重试次数")
                
            except (ConcurrentUpdateError, SQLAlchemyError) as e:
                logger.warning(f"更新结果时出错: {str(e)}")
                if retry_count >= max_retries - 1:
                    raise
                continue
        
        logger.info(f"作文批改完成 [essay_id={essay_id}]")
        return {
            "status": "success",
            "message": "作文批改完成",
            "essay_id": essay_id,
            "score": correction.score
        }
        
    except Exception as e:
        logger.error(f"作文批改任务处理失败 [essay_id={essay_id}]: {str(e)}")
        raise


@shared_task(bind=True)
def high_priority_essay_correction(self, essay_id: int) -> Dict[str, Any]:
    """
    高优先级的作文批改任务
    
    Args:
        essay_id: 作文ID
        
    Returns:
        Dict: 处理结果
    """
    logger.info(f"开始高优先级作文批改 [essay_id={essay_id}]")
    
    try:
        # 延迟导入模型，避免循环导入
        from app.models.essay import Essay
        from app.models.correction import Correction
        
        if not validate_essay_id(essay_id):
            return {"status": "error", "message": f"无效的作文ID: {essay_id}"}
        
        # 直接提交并等待结果
        result = process_essay_correction.apply_async(
            args=[essay_id],
            queue='high_priority'
        )
        # 返回任务ID，客户端可以用它来查询状态
        return {
            "status": "submitted",
            "task_id": result.id,
            "essay_id": essay_id,
            "message": "高优先级批改任务已提交"
        }
    except Exception as e:
        logger.exception(f"提交高优先级批改任务失败 [essay_id={essay_id}]: {str(e)}")
        return {
            "status": "error",
            "essay_id": essay_id,
            "message": f"提交高优先级批改任务失败: {str(e)}"
        }


@shared_task(bind=True)
def batch_process_essays(self, essay_ids: List[int]) -> Dict[str, Any]:
    """
    批量处理作文批改任务
    
    Args:
        essay_ids: 作文ID列表
        
    Returns:
        Dict: 处理结果
    """
    logger.info(f"开始批量处理作文批改，共{len(essay_ids)}个作文")
    results = {"success": [], "failed": []}
    
    try:
        # 延迟导入模型，避免循环导入
        from app.models.essay import Essay
        
        if not essay_ids or not isinstance(essay_ids, list):
            logger.error(f"无效的作文ID列表: {essay_ids}")
            return {"status": "error", "message": "无效的作文ID列表"}
        
        logger.info(f"开始批量处理作文批改任务，共{len(essay_ids)}篇作文")
        results = []
        task_ids = []
        
        for essay_id in essay_ids:
            if validate_essay_id(essay_id):
                try:
                    # 为每个作文提交单独的任务
                    result = process_essay_correction.apply_async(args=[essay_id])
                    task_ids.append(result.id)
                    results.append({
                        "essay_id": essay_id,
                        "task_id": result.id,
                        "status": "submitted"
                    })
                    logger.info(f"已提交作文批改任务 [essay_id={essay_id}, task_id={result.id}]")
                except Exception as e:
                    logger.error(f"提交批改任务失败 [essay_id={essay_id}]: {str(e)}")
                    results.append({
                        "essay_id": essay_id,
                        "status": "error",
                        "message": str(e)
                    })
            else:
                results.append({
                    "essay_id": essay_id,
                    "status": "error",
                    "message": "无效的作文ID"
                })
        
        return {
            "status": "batch_submitted",
            "total": len(essay_ids),
            "submitted": len(task_ids),
            "task_ids": task_ids,
            "results": results
        }
    except Exception as e:
        logger.exception(f"批量处理作文批改任务失败: {str(e)}")
        return {"status": "error", "message": f"批量处理作文批改任务失败: {str(e)}"}


@shared_task(bind=True)
def cleanup_stale_tasks(self) -> Dict[str, Any]:
    """
    清理滞留的任务
    
    查找并处理状态不一致或长时间未完成的任务
    
    Returns:
        Dict: 处理结果
    """
    logger.info("开始清理滞留任务")
    
    try:
        # 延迟导入模型，避免循环导入
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        
        stale_threshold = datetime.now() - timedelta(minutes=30)
        logger.info(f"开始清理过期任务，阈值时间: {stale_threshold}")
        
        with db.session() as session:
            # 查找所有状态为CORRECTING且开始时间超过阈值的批改记录
            stale_corrections = session.query(Correction).filter(
                Correction.status == CorrectionStatus.CORRECTING,
                Correction.started_at < stale_threshold
            ).all()
            
            if not stale_corrections:
                logger.info("没有发现需要清理的过期任务")
                return {"status": "success", "cleaned": 0, "message": "无过期任务"}
            
            cleaned_count = 0
            for correction in stale_corrections:
                essay = session.query(Essay).filter_by(id=correction.essay_id).first()
                if essay and essay.status == EssayStatus.CORRECTING:
                    # 更新作文和批改状态为失败
                    essay.status = EssayStatus.FAILED
                    correction.status = CorrectionStatus.FAILED
                    if hasattr(correction, 'error'):
                        correction.error = f"任务运行时间过长，已自动标记为失败"
                    else:
                        correction.error_message = f"任务运行时间过长，已自动标记为失败"
                    correction.completed_at = datetime.now()
                    cleaned_count += 1
                    logger.warning(f"清理过期任务: [essay_id={correction.essay_id}, task_id={correction.task_id}]")
            
            session.commit()
            logger.info(f"成功清理{cleaned_count}个过期任务")
            
            return {
                "status": "success", 
                "cleaned": cleaned_count,
                "message": f"已清理{cleaned_count}个过期任务"
            }
    except Exception as e:
        logger.exception(f"清理过期任务失败: {str(e)}")
        return {"status": "error", "message": f"清理过期任务失败: {str(e)}"}


@shared_task(bind=True)
def check_and_fix_inconsistent_statuses(self):
    """
    定期检查并修复不一致的状态
    
    检查Essay和Correction之间的状态一致性，以及处理长时间停留在CORRECTING状态的任务。
    根据任务实际状态对数据库记录进行修复。
    
    Returns:
        Dict[str, Any]: 包含执行结果的字典
    """
    logger.info("开始检查并修复状态不一致的记录")
    fixed_count = 0
    stale_count = 0
    
    try:
        # 延迟导入模型，避免循环导入
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        
        # 1. 查找状态不一致的记录
        with db.session() as session:
            # 使用join查询找出状态不一致的记录
            inconsistent_records = session.query(Essay, Correction).join(
                Correction, Essay.id == Correction.essay_id
            ).filter(
                ((Essay.status == EssayStatus.CORRECTING) & 
                 (Correction.status != CorrectionStatus.CORRECTING)) |
                ((Essay.status != EssayStatus.CORRECTING) & 
                 (Correction.status == CorrectionStatus.CORRECTING))
            ).all()
            
            logger.info(f"发现 {len(inconsistent_records)} 条状态不一致的记录")
            
            # 2. 修复不一致状态
            for essay, correction in inconsistent_records:
                logger.info(f"修复作文 {essay.id} 的状态不一致: {essay.status} vs {correction.status}")
                
                # 检查任务状态
                task_id = correction.task_id
                task_status = "UNKNOWN"
                
                if task_id:
                    from celery.result import AsyncResult
                    task_result = AsyncResult(task_id)
                    task_status = task_result.state
                    logger.info(f"作文 {essay.id} 对应的任务 {task_id} 状态为: {task_status}")
                
                try:
                    session.begin_nested()
                    
                    # 根据任务状态决定如何修复
                    if task_status in ["PENDING", "STARTED", "RETRY"]:
                        # 任务正在处理，保持CORRECTING状态
                        essay.status = EssayStatus.CORRECTING
                        correction.status = CorrectionStatus.CORRECTING
                        logger.info(f"将作文 {essay.id} 状态设置为处理中(任务仍在运行)")
                    elif task_status in ["SUCCESS"]:
                        # 任务已成功，但状态未更新
                        essay.status = EssayStatus.COMPLETED
                        correction.status = CorrectionStatus.COMPLETED
                        logger.info(f"将作文 {essay.id} 状态设置为已完成(任务已成功)")
                    elif task_status in ["FAILURE", "REVOKED"]:
                        # 任务已失败
                        essay.status = EssayStatus.FAILED
                        correction.status = CorrectionStatus.FAILED
                        if hasattr(correction, 'error_message') and not correction.error_message:
                            correction.error_message = "任务执行失败或被撤销"
                        elif hasattr(correction, 'error') and not correction.error:
                            correction.error = "任务执行失败或被撤销"
                        logger.info(f"将作文 {essay.id} 状态设置为失败(任务已失败)")
                    else:
                        # 任务状态未知或不存在，重置为待处理
                        essay.status = EssayStatus.PENDING
                        correction.status = CorrectionStatus.PENDING
                        correction.task_id = None
                        logger.info(f"将作文 {essay.id} 状态重置为待处理(任务状态未知)")
                    
                    session.commit()
                    fixed_count += 1
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"修复作文 {essay.id} 状态时出错: {str(e)}")
            
            # 3. 检查长时间处于CORRECTING状态的任务
            stale_time = datetime.now() - timedelta(hours=1)  # 1小时视为过期
            stale_corrections = session.query(Correction).filter(
                Correction.status == CorrectionStatus.CORRECTING
            ).all()
            
            # 筛选出更新时间超过阈值的记录
            stale_items = []
            for correction in stale_corrections:
                # 检查updated_at字段是否存在，不存在则使用其他时间字段
                update_time = None
                if hasattr(correction, 'updated_at') and correction.updated_at:
                    update_time = correction.updated_at
                elif hasattr(correction, 'started_at') and correction.started_at:
                    update_time = correction.started_at
                
                # 如果时间字段存在并且早于stale_time，则认为是滞留记录
                if update_time and update_time < stale_time:
                    stale_items.append(correction)
            
            logger.info(f"发现 {len(stale_items)} 条滞留的批改记录")
            
            for correction in stale_items:
                essay = session.query(Essay).get(correction.essay_id)
                if not essay:
                    logger.warning(f"找不到批改记录 {correction.id} 对应的作文 {correction.essay_id}")
                    continue
                    
                logger.warning(f"处理滞留的批改 {correction.id} (作文ID: {correction.essay_id})")
                
                # 检查任务状态
                task_id = correction.task_id
                if task_id:
                    from celery.result import AsyncResult
                    task_result = AsyncResult(task_id)
                    task_status = task_result.state
                    
                    try:
                        session.begin_nested()
                        
                        if task_status in ["PENDING", "STARTED", "RETRY"]:
                            # 尝试终止长时间运行的任务
                            try:
                                task_result.revoke(terminate=True)
                                logger.info(f"已终止滞留任务 {task_id}")
                            except Exception as revoke_error:
                                logger.error(f"终止任务 {task_id} 失败: {str(revoke_error)}")
                            
                            # 重置状态为待处理
                            essay.status = EssayStatus.PENDING
                            correction.status = CorrectionStatus.PENDING
                            correction.task_id = None
                            logger.info(f"已重置作文 {essay.id} 为待处理状态(长时间任务已终止)")
                        elif task_status == "SUCCESS":
                            # 任务已成功但状态未更新
                            essay.status = EssayStatus.COMPLETED
                            correction.status = CorrectionStatus.COMPLETED
                            logger.info(f"已将作文 {essay.id} 状态设置为已完成(滞留任务实际已完成)")
                        elif task_status in ["FAILURE", "REVOKED"]:
                            # 任务已失败
                            essay.status = EssayStatus.FAILED
                            correction.status = CorrectionStatus.FAILED
                            if hasattr(correction, 'error_message'):
                                correction.error_message = "任务执行失败或被撤销"
                            elif hasattr(correction, 'error'):
                                correction.error = "任务执行失败或被撤销"
                            logger.info(f"已将作文 {essay.id} 状态设置为失败(滞留任务已失败)")
                        else:
                            # 未知状态，重置为待处理
                            essay.status = EssayStatus.PENDING
                            correction.status = CorrectionStatus.PENDING
                            correction.task_id = None
                            logger.info(f"已重置作文 {essay.id} 为待处理状态(滞留任务状态未知)")
                        
                        session.commit()
                        stale_count += 1
                    except SQLAlchemyError as e:
                        session.rollback()
                        logger.error(f"处理滞留的批改 {correction.id} 时出错: {str(e)}")
                else:
                    # 没有任务ID但状态为CORRECTING，直接重置为待处理
                    try:
                        session.begin_nested()
                        essay.status = EssayStatus.PENDING
                        correction.status = CorrectionStatus.PENDING
                        session.commit()
                        logger.info(f"已重置作文 {essay.id} 为待处理状态(无关联任务ID)")
                        stale_count += 1
                    except SQLAlchemyError as e:
                        session.rollback()
                        logger.error(f"重置作文 {essay.id} 状态时出错: {str(e)}")
        
        return {
            "status": "success", 
            "fixed_count": fixed_count,
            "stale_count": stale_count,
            "message": f"状态检查和修复完成，修复了 {fixed_count} 条不一致记录，处理了 {stale_count} 条滞留记录"
        }
    except Exception as e:
        logger.exception(f"状态检查和修复过程出错: {str(e)}")
        return {
            "status": "error",
            "message": f"状态检查和修复过程出错: {str(e)}"
        }


@shared_task(bind=True)
def schedule_status_consistency_check(self):
    """
    调度状态一致性检查任务
    
    此任务定期调度运行check_and_fix_inconsistent_statuses任务，
    用于检测和修复系统中的状态不一致问题。
    
    Returns:
        Dict[str, Any]: 包含调度结果的字典
    """
    try:
        logger.info("调度状态一致性检查任务")
        result = check_and_fix_inconsistent_statuses.apply_async()
        return {
            "status": "success",
            "task_id": result.id,
            "message": "已成功调度状态一致性检查任务"
        }
    except Exception as e:
        logger.exception(f"调度状态一致性检查任务失败: {str(e)}")
        return {
            "status": "error",
            "message": f"调度任务失败: {str(e)}"
        } 