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
from celery import Celery

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
    bind=True,
    name='app.tasks.correction_tasks.process_essay_correction',
    max_retries=3,
    default_retry_delay=300,
    acks_late=True
)
def process_essay_correction(self, essay_id):
    """处理作文批改任务"""
    try:
        # 注意：不再创建应用上下文，因为这已经在task_prerun信号处理中完成
        logger.info(f"开始处理作文批改任务: essay_id={essay_id}")
        
        try:
            # 获取作文信息
            essay = Essay.query.get(essay_id)
            if not essay:
                logger.error(f"找不到作文: essay_id={essay_id}")
                return {'success': False, 'error': 'Essay not found'}
            
            # 安全地获取grade字段，如果不存在则为None
            grade = None
            try:
                grade = essay.grade
                logger.debug(f"作文年级: essay_id={essay_id}, grade={grade}")
            except (AttributeError, Exception) as e:
                # 如果字段不存在或访问出错，记录日志但不终止流程
                logger.warning(f"获取作文年级字段失败，可能是旧数据: essay_id={essay_id}, error={str(e)}")
            
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
                    logger.error(f"无法将作文状态更新为处理中: essay_id={essay_id}")
                    return {'success': False, 'error': '状态更新失败'}
                
                correction.status = CorrectionStatus.PROCESSING.value
                db.session.flush()
            
            # 提交事务
            db.session.commit()
            
            # 获取批改服务
            from app.core.services.container import container
            correction_service = container.get("correction_service")
            if not correction_service:
                logger.error("Correction service not found")
                return {'success': False, 'error': 'Correction service not found'}
            
            # 执行批改
            result = correction_service.perform_correction(essay_id)
            
            # 处理成功，更新状态和结果
            try:
                with db.session.begin_nested():
                    # 验证评分结果
                    scores = result.get('results', {}).get('scores', {})
                    if not validate_scores(scores):
                        raise ValueError("Invalid scores in correction results")
                    
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
                        raise ValueError("Failed to update essay status to completed")
                    
                    # 同步结果到Essay
                    correction.sync_results_to_essay()
                
                # 提交事务
                db.session.commit()
                
                logger.info(f"作文批改完成: essay_id={essay_id}")
                return {
                    'success': True,
                    'essay_id': essay_id,
                    'correction_id': correction.id,
                    'results': result.get('results')
                }
            
            except Exception as e:
                logger.error(f"更新批改结果失败: essay_id={essay_id}, error={str(e)}")
                db.session.rollback()
                raise
        
        except Exception as e:
            logger.error(f"处理作文批改任务发生未预期错误: essay_id={essay_id}, error={str(e)}")
            # 重试任务
            raise self.retry(exc=e)
    finally:
        # 确保数据库会话在任务结束时被清理
        # 注意：应用上下文的清理由task_postrun信号处理
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
    if total_score < min(content_score, language_score) or total_score > max(content_score, language_score):
        return False
    
    return True

@celery_app.task
def cleanup_stale_tasks():
    """清理停滞的任务"""
    try:
        # 注意：不再手动创建应用上下文，依赖于task_prerun信号处理
        # 查找所有处于pending或processing状态超过1小时的作文
        from datetime import datetime, timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        stale_essays = Essay.query.filter(
            Essay.status.in_(['pending', 'processing']),
            Essay.updated_at < one_hour_ago
        ).all()
        
        for essay in stale_essays:
            # 重新提交批改任务
            process_essay_correction.apply_async(args=[essay.id])
            logger.info(f"重新提交停滞的作文批改任务: essay_id={essay.id}")
            
    except Exception as e:
        logger.error(f"清理停滞任务时出错: {str(e)}")
    finally:
        # 确保数据库会话在任务结束时被清理
        db.session.remove()

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
    from app.core.ai.init_services import ensure_services
    from app.extensions import db
    
    flask_app = create_app()
    
    # 保存应用上下文到Celery任务实例
    if not hasattr(self, 'app_context'):
        self.app_context = flask_app.app_context()
        self.app_context.push()
        
    try:
        # 确保有新的干净的数据库会话
        db.session.remove()
        
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
            'message': f"已处理 {len(essay_ids)} 篇作文，成功 {len(results)} 篇，失败 {len(errors)} 篇",
            'results': results,
            'errors': errors,
            'task_id': task_id
        }
    finally:
        # 确保数据库会话在任务结束时被清理
        db.session.remove()
        
        # 确保上下文在任务结束时被正确清理
        if hasattr(self, 'app_context'):
            try:
                self.app_context.pop()
            except Exception as e:
                logger.warning(f"清理应用上下文时出错: {str(e)}")

def update_essay_status(essay_id, status, error=None):
    """
    更新作文状态
    
    Args:
        essay_id: 作文ID
        status: 状态 (pending/processing/completed/failed)
        error: 错误信息（如果有）
    """
    try:
        with db.session() as session:
            essay = session.query(Essay).get(essay_id)
            if essay:
                # 使用枚举值更新状态
                if status == 'pending':
                    essay.status = EssayStatus.PENDING.value
                elif status == 'processing' or status == 'correcting':
                    essay.status = EssayStatus.CORRECTING.value
                elif status == 'completed':
                    essay.status = EssayStatus.COMPLETED.value
                elif status == 'failed':
                    essay.status = EssayStatus.FAILED.value
                else:
                    essay.status = EssayStatus.PENDING.value
                
                if error:
                    essay.error_message = error
                session.commit()
                logger.info(f"更新作文状态为: {essay.status}，ID: {essay_id}")
    except Exception as e:
        logger.error(f"更新作文状态失败，ID: {essay_id}: {str(e)}") 