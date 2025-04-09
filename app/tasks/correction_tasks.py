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
from app.models.essay import Essay
from app.models.correction import Correction
from app.extensions import db
from app.models.correction_type import CorrectionType
from app.models.correction_status import CorrectionStatus
from app.models.essay_status import EssayStatus
from app.models.task_status import TaskStatus, TaskState

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
    task_soft_time_limit=600,  # 10分钟
    queue='correction'
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
    from app.core.services.init_services import ensure_services
    
    app = create_app()
    
    with app.app_context():
        # 确保所有必要的服务已初始化
        if not ensure_services():
            logger.error(f"[{task_id}] 服务初始化失败, essay_id={essay_id}")
            return {
                'status': 'error',
                'message': "服务初始化失败",
                'task_id': task_id
            }
            
        # 记录任务状态
        try:
            # 查找或创建任务状态记录
            task_status = TaskStatus.query.filter_by(task_id=task_id).first()
            if not task_status:
                task_status = TaskStatus.create_from_task(
                    task_id=task_id,
                    task_name='process_essay_correction',
                    related_type='essay',
                    related_id=str(essay_id),
                    args=json.dumps([essay_id]),
                    worker_id=self.request.hostname
                )
            
            # 更新为开始状态
            task_status.mark_as_started()
            
        except Exception as e:
            logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
        
        try:
            # 获取作文，提前验证
            essay = Essay.query.get(essay_id)
            if not essay:
                error_msg = f"作文不存在，ID: {essay_id}"
                logger.error(f"[{task_id}] {error_msg}")
                
                # 更新任务状态
                if 'task_status' in locals():
                    task_status.mark_as_failure(error=error_msg)
                    
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
                    # 增加重试计数
                    task_status.increment_retry()
                    
                # 使用合适的重试策略
                policy = get_retry_policy('app.tasks.correction_tasks.process_essay_correction', AttributeError())
                retry_delay = calculate_next_retry_time(
                    self.request.retries,
                    policy['base_delay'],
                    policy['max_delay']
                )
                
                raise self.retry(exc=AttributeError('Essay对象缺少source_type属性'), countdown=retry_delay)
            
            # 检查作文状态
            if essay.status == EssayStatus.COMPLETED.value:
                logger.info(f"[{task_id}] 作文已完成批改，跳过处理，ID: {essay_id}")
                
                if 'task_status' in locals():
                    task_status.mark_as_success(result={'status': 'skipped', 'reason': '作文已完成批改'})
                    
                return {
                    'status': 'skipped',
                    'message': '作文已完成批改',
                    'task_id': task_id
                }
            
            # 使用事务确保状态更新的原子性
            with db.session.begin_nested():
                # 获取或创建批改记录
                correction = Correction.query.filter_by(essay_id=essay_id).first()
                if not correction:
                    correction = Correction(
                        essay_id=essay_id,
                        type=CorrectionType.AI.value,
                        status=CorrectionStatus.PENDING.value
                    )
                    db.session.add(correction)
                    db.session.flush()
                
                # 更新状态为处理中
                if not essay.update_status(EssayStatus.CORRECTING):
                    error_msg = f"无法将作文状态更新为处理中: essay_id={essay_id}"
                    logger.error(f"[{task_id}] {error_msg}")
                    
                    if 'task_status' in locals():
                        task_status.mark_as_failure(error=error_msg)
                        
                    return {
                        'status': 'error',
                        'message': error_msg,
                        'task_id': task_id
                    }
                
                correction.status = CorrectionStatus.PROCESSING.value
                db.session.flush()
            
            # 提交事务
            db.session.commit()
                
            # 获取批改服务
            from app.core.services.container import container
            correction_service = container.get("correction_service")
            if not correction_service:
                error_msg = "Correction service not found"
                logger.error(f"[{task_id}] {error_msg}")
                
                if 'task_status' in locals():
                    task_status.mark_as_failure(error=error_msg)
                    
                return {
                    'status': 'error',
                    'message': error_msg,
                    'task_id': task_id
                }
            
            # 执行批改
            logger.info(f"[{task_id}] 开始执行批改，作文ID: {essay_id}")
            result = correction_service.perform_correction(essay_id)
            logger.info(f"[{task_id}] 批改执行完成，作文ID: {essay_id}, 状态: {result.get('status')}")
            
            # 处理成功，更新状态和结果
            if result.get('status') == 'success':
                try:
                    with db.session.begin_nested():
                        # 验证评分结果
                        scores = result.get('results', {}).get('scores', {})
                        if not validate_scores(scores):
                            raise ValueError("评分结果无效")
                        
                        # 更新批改记录
                        correction.results = result.get('results')
                        correction.score = scores.get('total_score')
                        correction.content = result.get('results', {}).get('corrected_content')
                        correction.comments = result.get('results', {}).get('comments')
                        correction.error_analysis = result.get('results', {}).get('error_analysis')
                        correction.improvement_suggestions = result.get('results', {}).get('improvement_suggestions')
                        correction.status = CorrectionStatus.COMPLETED.value
                        correction.completed_at = datetime.utcnow()
                        
                        # 更新作文状态为完成
                        if not essay.update_status(EssayStatus.COMPLETED):
                            raise ValueError("更新作文状态为完成失败")
                        
                        # 同步结果到Essay
                        correction.sync_results_to_essay()
                    
                    # 提交事务
                    db.session.commit()
                    
                    # 记录任务成功
                    if 'task_status' in locals():
                        task_status.mark_as_success(result={
                            'essay_id': essay_id,
                            'correction_id': correction.id,
                            'score': correction.score
                        })
                    
                    logger.info(f"[{task_id}] 作文批改完成并保存结果: essay_id={essay_id}")
                    return {
                        'status': 'success',
                        'essay_id': essay_id,
                        'correction_id': correction.id,
                        'results': result.get('results'),
                        'task_id': task_id
                    }
                
                except Exception as e:
                    error_msg = f"更新批改结果失败: {str(e)}"
                    logger.error(f"[{task_id}] {error_msg}, essay_id={essay_id}")
                    db.session.rollback()
                    
                    if 'task_status' in locals():
                        task_status.mark_as_failure(error=error_msg)
                    
                    # 设置作文状态为错误
                    try:
                        with db.session.begin_nested():
                            essay.update_status(EssayStatus.ERROR)
                            correction.status = CorrectionStatus.ERROR.value
                            correction.error = str(e)
                        db.session.commit()
                    except Exception as ex:
                        logger.error(f"[{task_id}] 更新失败状态时出错: {str(ex)}")
                        db.session.rollback()
                    
                    raise
            else:
                # 批改执行失败
                error_msg = result.get('message', '批改执行失败，未返回详细错误')
                logger.error(f"[{task_id}] 批改执行失败: {error_msg}, essay_id={essay_id}")
                
                # 更新状态为错误
                try:
                    with db.session.begin_nested():
                        essay.update_status(EssayStatus.ERROR)
                        correction.status = CorrectionStatus.ERROR.value
                        correction.error = error_msg
                    db.session.commit()
                except Exception as ex:
                    logger.error(f"[{task_id}] 更新失败状态时出错: {str(ex)}")
                    db.session.rollback()
                
                if 'task_status' in locals():
                    task_status.mark_as_failure(error=error_msg)
                
                return {
                    'status': 'error',
                    'message': error_msg,
                    'task_id': task_id
                }
        
        except self.retry_error as e:
            # 重试异常不需要记录故障，因为任务将重试
            logger.info(f"[{task_id}] 任务将重试: {str(e)}")
            raise
            
        except Exception as e:
            error_msg = f"处理作文批改任务发生未预期错误: {str(e)}"
            logger.error(f"[{task_id}] {error_msg}, essay_id={essay_id}")
            logger.error(f"[{task_id}] 详细错误: {traceback.format_exc()}")
            
            # 更新状态为错误
            try:
                with db.session.begin_nested():
                    # 只有当作文存在时才更新状态
                    if 'essay' in locals() and essay:
                        essay.update_status(EssayStatus.ERROR)
                    
                    # 只有当批改记录存在时才更新状态
                    if 'correction' in locals() and correction:
                        correction.status = CorrectionStatus.ERROR.value
                        correction.error = str(e)
                db.session.commit()
            except Exception as ex:
                logger.error(f"[{task_id}] 更新失败状态时出错: {str(ex)}")
                db.session.rollback()
            
            if 'task_status' in locals():
                task_status.mark_as_failure(error=error_msg)
            
            # 检查是否应该重试任务
            if should_retry_task(e, self.request.retries, 5):
                policy = get_retry_policy('app.tasks.correction_tasks.process_essay_correction', e)
                retry_delay = calculate_next_retry_time(
                    self.request.retries,
                    policy['base_delay'],
                    policy['max_delay']
                )
                
                logger.info(f"[{task_id}] 任务将在 {retry_delay} 秒后重试，当前重试次数: {self.request.retries}")
                raise self.retry(exc=e, countdown=retry_delay)
            else:
                logger.error(f"[{task_id}] 任务失败且不再重试，已达到最大重试次数或错误类型不支持重试")
                return {
                    'status': 'error',
                    'message': error_msg,
                    'task_id': task_id
                }
        finally:
            # 确保数据库会话在任务结束时被清理
            db.session.remove()

def validate_scores(scores):
    """验证评分结果的有效性"""
    if not isinstance(scores, dict):
        return False
    
    required_fields = ['total_score', 'content_score', 'language_score']
    if not all(field in scores for field in required_fields):
        return False
    
    # 验证分数范围
    for field in required_fields:
        score = scores.get(field)
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            return False
    
    # 验证总分计算
    total_score = scores['total_score']
    content_score = scores['content_score']
    language_score = scores['language_score']
    
    # 总分应该在内容分和语言分的范围内
    if total_score < min(content_score, language_score) or total_score > max(content_score, language_score) + 10:
        return False
    
    return True

@celery_app.task(
    name='app.tasks.correction_tasks.high_priority_essay_correction',
    bind=True,
    max_retries=5,
    default_retry_delay=60,
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
                    
                if essay.status == EssayStatus.COMPLETED.value:
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

@celery_app.task
def cleanup_stale_tasks():
    """清理停滞的任务"""
    # 获取任务专用日志记录器
    logger = get_task_logger()
    
    # 创建Flask应用上下文
    from app import create_app
    
    with create_app().app_context():
        try:
            # 查找长时间处于运行状态的任务
            from app.models.task_status import TaskStatus, TaskState
            from datetime import timedelta
            
            # 查找超过1小时仍在运行的任务
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            stale_tasks = TaskStatus.query.filter(
                TaskStatus.status == TaskState.RUNNING,
                TaskStatus.started_at < cutoff_time
            ).all()
            
            if not stale_tasks:
                logger.info("没有发现停滞的任务")
                return {"status": "success", "message": "No stale tasks found"}
                
            logger.info(f"发现 {len(stale_tasks)} 个停滞的任务")
            
            for task in stale_tasks:
                logger.info(f"标记停滞任务为失败: {task.task_id}, 任务名称: {task.task_name}, 运行时长: {task.duration}秒")
                task.mark_as_failure(error="Task marked as failed due to timeout")
                
                # 如果是作文批改任务，更新相关作文状态
                if task.related_type == 'essay' and task.related_id:
                    try:
                        essay = Essay.query.get(int(task.related_id))
                        if essay and essay.status == EssayStatus.CORRECTING.value:
                            essay.update_status(EssayStatus.ERROR)
                            
                            # 更新批改记录
                            correction = Correction.query.filter_by(essay_id=essay.id).first()
                            if correction:
                                correction.status = CorrectionStatus.ERROR.value
                                correction.error = "Task timeout"
                                db.session.commit()
                                logger.info(f"已更新相关作文状态: essay_id={essay.id}")
                    except Exception as e:
                        logger.error(f"更新相关作文状态失败: {str(e)}")
            
            return {
                "status": "success",
                "message": f"Marked {len(stale_tasks)} stale tasks as failed"
            }
        
        except Exception as e:
            logger.error(f"清理停滞任务失败: {str(e)}")
            return {"status": "error", "message": str(e)} 