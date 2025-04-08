#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改异步任务模块
提供作文批改相关的异步任务处理
"""

import logging
import traceback
import json
from datetime import datetime
import uuid

from app.tasks.celery_app import celery_app
from app.core.correction.correction_service import CorrectionService
from app.tasks.retry_strategies import should_retry_task, calculate_next_retry_time, get_retry_policy
from app.tasks.logging_config import get_task_logger

# 获取任务专用日志记录器
logger = get_task_logger()

def validate_essay_id(essay_id):
    """
    验证作文ID
    
    Args:
        essay_id: 作文ID
        
    Returns:
        tuple: (bool, str) - (是否有效, 错误消息)
    """
    # 检查是否为None或空
    if essay_id is None:
        return False, "作文ID不能为空"
        
    # 检查类型
    if not isinstance(essay_id, int) and not (isinstance(essay_id, str) and essay_id.isdigit()):
        return False, f"作文ID必须是整数，当前类型: {type(essay_id)}"
        
    # 转换为整数并检查范围
    try:
        essay_id = int(essay_id)
        if essay_id <= 0:
            return False, f"作文ID必须是正整数，当前值: {essay_id}"
    except (ValueError, TypeError):
        return False, f"无法将作文ID转换为整数: {essay_id}"
        
    return True, ""

@celery_app.task(
    name='app.tasks.correction_tasks.process_essay_correction',
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    task_time_limit=900,  # 15分钟
    task_soft_time_limit=600  # 10分钟
)
def process_essay_correction(self, essay_id):
    """
    异步处理作文批改任务
    
    Args:
        self: Celery任务实例
        essay_id: 作文ID
    
    Returns:
        Dict: 批改结果
    """
    task_id = self.request.id or str(uuid.uuid4())
    
    # 记录任务开始信息
    logger.info(f"[{task_id}] 开始异步处理作文批改，作文ID: {essay_id}")
    
    # 参数验证
    is_valid, error_message = validate_essay_id(essay_id)
    if not is_valid:
        logger.error(f"[{task_id}] 作文ID无效: {error_message}")
        return {
            'status': 'error',
            'message': error_message,
            'task_id': task_id
        }
    
    # 转换为整数
    essay_id = int(essay_id)
    
    # 创建Flask应用上下文
    from app import create_app
    from flask import current_app
    from app.core.ai.init_services import ensure_services
    
    # 确保所有必要的服务已初始化
    if not ensure_services():
        current_app.logger.error(f"Essay correction failed: services initialization failed for essay_id={essay_id}")
        return {"status": "error", "message": "Services initialization failed"}
    
    with create_app().app_context():
        # 记录任务状态
        try:
            from app.models.task_status import TaskStatus, TaskState
            from app.models.db import db
            
            # 查找或创建任务状态记录
            task_status = TaskStatus.find_by_task_id(task_id)
            if not task_status:
                task_status = TaskStatus.create_from_task(
                    task_id=task_id,
                    task_name='process_essay_correction',
                    related_type='essay',
                    related_id=essay_id,
                    args=json.dumps([essay_id]),
                    worker_id=self.request.hostname
                )
            
            # 更新为开始状态
            task_status.mark_as_started()
            
        except Exception as e:
            logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
        
        try:
            # 获取作文，提前验证
            from app.models.essay import Essay
            essay = Essay.query.get(essay_id)
            if not essay:
                error_msg = f"作文不存在，ID: {essay_id}"
                logger.error(f"[{task_id}] {error_msg}")
                
                # 更新任务状态
                if 'task_status' in locals():
                    task_status.mark_as_failure(error_message=error_msg)
                    
                return {
                    'status': 'error',
                    'message': error_msg,
                    'task_id': task_id
                }
            
            # 强制类型检查
            if not hasattr(essay, 'source_type'):
                error_msg = f"Essay对象缺少source_type属性，ID: {essay_id}"
                logger.warning(f"[{task_id}] {error_msg}，尝试重试")
                
                if 'task_status' in locals():
                    # 计算下次重试时间
                    policy = get_retry_policy('app.tasks.correction_tasks.process_essay_correction', AttributeError())
                    next_retry = calculate_next_retry_time(
                        self.request.retries,
                        policy['base_delay'],
                        policy['max_delay']
                    )
                    
                    task_status.mark_as_retry(
                        next_retry_at=next_retry,
                        error_message=error_msg
                    )
                    
                raise AttributeError('Essay对象缺少source_type属性')
            
            # 检查作文状态
            if essay.status == 'completed':
                logger.info(f"[{task_id}] 作文已完成批改，跳过处理，ID: {essay_id}")
                
                if 'task_status' in locals():
                    task_status.mark_as_success(result={'status': 'skipped', 'reason': '作文已完成批改'})
                    
                return {
                    'status': 'skipped',
                    'message': '作文已完成批改',
                    'task_id': task_id
                }
                
            # 获取批改服务
            from app.core.services.container import container
            correction_service = container.get("correction_service")
            if not correction_service:
                logger.error(f"[{task_id}] Correction service not found")
                
                if 'task_status' in locals():
                    task_status.mark_as_failure(error_message="Correction service not found")
                    
                return {
                    'status': 'error',
                    'message': 'Correction service not found',
                    'task_id': task_id
                }
        
            # 执行批改
            logger.info(f"[{task_id}] 开始执行批改，作文ID: {essay_id}")
            result = correction_service.perform_correction(essay_id)
            logger.info(f"[{task_id}] 批改执行完成，作文ID: {essay_id}, 状态: {result.get('status')}")
            
            # 处理结果
            if result.get('status') == 'success':
                logger.info(f"[{task_id}] 作文批改成功，作文ID: {essay_id}")
                
                if 'task_status' in locals():
                    task_status.mark_as_success(result=result)
                    
            else:
                logger.warning(f"[{task_id}] 作文批改失败，作文ID: {essay_id}, 原因: {result.get('message', '未知错误')}")
                
                if 'task_status' in locals():
                    task_status.mark_as_failure(
                        error_message=result.get('message', '未知错误')
                    )
        
            return result
        
        except Exception as e:
            # 输出详细错误信息
            error_tb = traceback.format_exc()
            logger.error(f"[{task_id}] 处理作文批改任务异常，作文ID: {essay_id}, 错误: {str(e)}")
            logger.error(f"[{task_id}] 错误堆栈: {error_tb}")
            
            # 更新作文状态为失败
            try:
                from app.models.essay import Essay
                from app.models.correction import Correction
                from app.models.db import db
                
                essay = Essay.query.get(essay_id)
                if essay and essay.status != 'failed':
                    essay.status = 'failed'
                    db.session.commit()
                    logger.info(f"[{task_id}] 已将作文状态更新为失败，ID: {essay_id}")
            except Exception as db_error:
                logger.error(f"[{task_id}] 更新作文状态失败: {str(db_error)}")
            
            # 判断是否应该重试
            retry_count = self.request.retries
            policy = get_retry_policy('app.tasks.correction_tasks.process_essay_correction', e)
            max_retries = policy['max_retries']
            
            if should_retry_task(e, retry_count, max_retries):
                # 计算重试延迟
                retry_delay = policy['base_delay'] * (2 ** retry_count)
                if retry_delay > policy['max_delay']:
                    retry_delay = policy['max_delay']
                    
                logger.info(f"[{task_id}] 将在 {retry_delay} 秒后进行第 {retry_count+1}/{max_retries} 次重试")
                
                if 'task_status' in locals():
                    next_retry = calculate_next_retry_time(
                        retry_count,
                        policy['base_delay'],
                        policy['max_delay']
                    )
                    
                    task_status.mark_as_retry(
                        next_retry_at=next_retry,
                        error_message=str(e),
                        traceback=error_tb
                    )
                
                # 触发重试
                self.retry(exc=e, countdown=retry_delay, max_retries=max_retries)
            else:
                # 重试次数已达上限或不应该重试的错误
                logger.error(f"[{task_id}] 作文批改任务不再重试，原因: {str(e)}")
                
                if 'task_status' in locals():
                    task_status.mark_as_failure(
                        error_message=str(e),
                        traceback=error_tb
                    )
                    
                # 发送任务失败通知
                try:
                    from app.tasks.notification_tasks import send_task_failure_notification
                    send_task_failure_notification.delay(
                        task_id=task_id,
                        related_type='essay',
                        related_id=essay_id,
                        error_message=str(e)
                    )
                    logger.info(f"[{task_id}] 已触发任务失败通知")
                except Exception as notify_error:
                    logger.error(f"[{task_id}] 触发任务失败通知时出错: {str(notify_error)}")
                
                return {
                    'status': 'error',
                    'message': f'批改任务异常: {str(e)}',
                    'task_id': task_id,
                    'essay_id': essay_id,
                    'retry_count': retry_count
                }

@celery_app.task(
    name='app.tasks.correction_tasks.high_priority_essay_correction',
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
    task_time_limit=600,  # 10分钟
    task_soft_time_limit=300,  # 5分钟
    queue='correction.priority'
)
def high_priority_essay_correction(self, essay_id):
    """
    高优先级作文批改任务
    
    Args:
        self: Celery任务实例
        essay_id: 作文ID
    
    Returns:
        Dict: 批改结果
    """
    # 将任务优先级添加到请求上下文
    setattr(self.request, 'priority', 9)
    
    # 复用现有的批改任务实现
    return process_essay_correction(self, essay_id)


@celery_app.task(
    name='app.tasks.correction_tasks.batch_process_essays',
    bind=True,
    max_retries=3,
    acks_late=True,
    task_time_limit=1800,  # 30分钟
    queue='correction'
)
def batch_process_essays(self, essay_ids, priority=False):
    """
    批量处理作文批改任务
    
    Args:
        self: Celery任务实例
        essay_ids: 作文ID列表
        priority: 是否高优先级
    
    Returns:
        Dict: 批处理结果
    """
    task_id = self.request.id or str(uuid.uuid4())
    
    # 记录任务开始信息
    logger.info(f"[{task_id}] 开始批量处理作文批改, 共 {len(essay_ids)} 篇作文")
    
    # 创建Flask应用上下文
    from app import create_app
    from flask import current_app
    from app.core.ai.init_services import ensure_services
    
    app = create_app()
    
    with app.app_context():
        # 确保所有必要的服务已初始化
        if not ensure_services():
            logger.error(f"[{task_id}] 批量处理作文批改失败：服务初始化失败")
            return {
                'status': 'error',
                'message': "服务初始化失败",
                'task_id': task_id
            }
        
        # 参数验证
        if not essay_ids or not isinstance(essay_ids, list):
            error_msg = f"作文ID列表无效或为空: {essay_ids}"
            logger.error(f"[{task_id}] {error_msg}")
            return {
                'status': 'error',
                'message': error_msg,
                'task_id': task_id
            }
        
        # 记录任务状态
        try:
            from app.models.task_status import TaskStatus
            
            # 创建批处理任务状态
            batch_task = TaskStatus.create_from_task(
                task_id=task_id,
                task_name='batch_process_essays',
                related_type='batch',
                args=json.dumps(essay_ids),
                worker_id=self.request.hostname
            )
            
            batch_task.mark_as_started()
            batch_task.update_metadata({
                'total_essays': len(essay_ids),
                'priority': priority
            })
            
        except Exception as e:
            logger.warning(f"[{task_id}] 记录批处理任务状态失败: {str(e)}")
        
        # 提交单个任务结果
        results = []
        errors = []
        success_count = 0
        
        # 选择合适的任务函数
        correction_task = high_priority_essay_correction if priority else process_essay_correction
        
        # 逐个提交任务
        for essay_id in essay_ids:
            try:
                # 检查作文是否存在且未处理
                from app.models.essay import Essay
                essay = Essay.query.get(essay_id)
                
                if not essay:
                    error_msg = f"作文不存在，ID: {essay_id}"
                    logger.warning(f"[{task_id}] {error_msg}")
                    errors.append({
                        'essay_id': essay_id,
                        'error': error_msg
                    })
                    continue
                    
                if essay.status == 'completed':
                    logger.info(f"[{task_id}] 作文已完成批改，跳过处理，ID: {essay_id}")
                    success_count += 1
                    results.append({
                        'essay_id': essay_id,
                        'status': 'skipped',
                        'message': '作文已完成批改'
                    })
                    continue
                
                # 提交任务
                task_result = correction_task.delay(essay_id)
                logger.info(f"[{task_id}] 已提交作文批改任务，作文ID: {essay_id}, 任务ID: {task_result.id}")
                
                # 记录结果
                results.append({
                    'essay_id': essay_id,
                    'task_id': task_result.id,
                    'status': 'submitted'
                })
                
            except Exception as e:
                error_msg = f"提交作文批改任务失败: {str(e)}"
                logger.error(f"[{task_id}] {error_msg}, 作文ID: {essay_id}")
                errors.append({
                    'essay_id': essay_id,
                    'error': error_msg
                })
        
        # 更新批处理任务状态
        if 'batch_task' in locals():
            batch_task.mark_as_success(result={
                'total': len(essay_ids),
                'submitted': len(results),
                'errors': len(errors),
                'skipped': success_count
            })
    
        return {
            'status': 'success' if not errors else 'partial',
            'total': len(essay_ids),
            'submitted': len(results),
            'errors': len(errors),
            'results': results,
            'error_details': errors
        } 