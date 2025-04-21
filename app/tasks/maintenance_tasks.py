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
import traceback  # 添加traceback导入
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import SQLAlchemyError
from celery.result import AsyncResult
from sqlalchemy import text, func, or_, and_
from flask import has_app_context, current_app

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

@celery_app.task(name="maintenance.check_essay_statuses")
def check_essay_statuses():
    """
    检查作文状态，处理长时间处于处理状态的作文
    返回:
        dict: 包含处理结果的字典
    """
    try:
        # 记录任务开始
        task_id = record_task_status("check_essay_statuses", "started")
        
        logger.info("开始检查作文状态")
        
        # 确保在Flask应用上下文中执行
        if not has_app_context():
            # 如果不在应用上下文中，创建一个新的上下文
            from app import create_app
            app = create_app()
            with app.app_context():
                return _process_check_essay_statuses(task_id)
        else:
            # 如果已在应用上下文中，直接执行
            return _process_check_essay_statuses(task_id)
            
    except Exception as e:
        logger.error(f"检查作文状态失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 记录任务失败
        if task_id:
            update_task_status(task_id, "failed", error=str(e))
        
        return {
            "status": "error",
            "message": str(e),
            "processed_count": 0
        }

def _process_check_essay_statuses(task_id):
    """实际处理作文状态检查的内部函数"""
    try:
        # 查找长时间处于处理中状态的作文
        stale_time = datetime.utcnow() - timedelta(hours=2)  # 2小时视为过期
        stale_essays = Essay.query.filter(
            Essay.status == 'correcting',
            Essay.updated_at < stale_time
        ).all()
        
        if not stale_essays:
            logger.info("没有发现滞留的作文")
            
            # 更新任务状态
            update_task_status(task_id, "completed", result={
                "message": "没有发现滞留的作文",
                "processed_count": 0
            })
            
            return {
                "status": "success",
                "message": "没有发现滞留的作文",
                "processed_count": 0
            }
        
        # 记录滞留的作文数量
        logger.info(f"发现 {len(stale_essays)} 篇滞留的作文")
        
        # 处理滞留的作文
        processed_count = 0
        for essay in stale_essays:
            try:
                logger.info(f"处理滞留作文: essay_id={essay.id}, 状态={essay.status}, 更新时间={essay.updated_at}")
                
                # 获取相关的批改记录
                correction = Correction.query.filter_by(essay_id=essay.id).first()
                
                if not correction:
                    logger.warning(f"作文 {essay.id} 没有关联的批改记录")
                    # 将作文状态重置为pending
                    essay.status = 'pending'
                    db.session.add(essay)
                    processed_count += 1
                    continue
                
                # 检查任务状态
                task_id = correction.task_id
                if task_id:
                    task_result = AsyncResult(task_id, app=celery_app)
                    task_status = task_result.state
                    logger.info(f"任务 {task_id} 的状态为: {task_status}")
                    
                    if task_status in ["PENDING", "STARTED", "RETRY"]:
                        # 任务仍在处理但时间过长，重置为待处理状态
                        logger.info(f"任务 {task_id} 运行时间过长，重置状态")
                        essay.status = 'pending'
                        correction.status = 'pending'
                        correction.task_id = None
                    elif task_status == "SUCCESS":
                        # 任务已成功但状态未更新
                        essay.status = 'completed'
                        correction.status = 'completed'
                        logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为completed")
                    elif task_status in ["FAILURE", "REVOKED"]:
                        # 任务已失败
                        essay.status = 'failed'
                        correction.status = 'failed'
                        correction.error = "任务执行失败或被撤销"
                        logger.info(f"更新作文 {essay.id} 和批改 {correction.id} 的状态为failed")
                    else:
                        # 未知状态，重置为待处理
                        essay.status = 'pending'
                        correction.status = 'pending'
                        correction.task_id = None
                        logger.info(f"未知任务状态，重置作文 {essay.id} 和批改 {correction.id} 的状态为pending")
                else:
                    # 没有任务ID，重置为待处理
                    essay.status = 'pending'
                    correction.status = 'pending'
                    logger.info(f"批改记录无任务ID，重置作文 {essay.id} 和批改 {correction.id} 的状态为pending")
                
                db.session.add(essay)
                db.session.add(correction)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"处理作文 {essay.id} 时出错: {str(e)}")
                logger.error(traceback.format_exc())
        
        # 提交所有更改
        db.session.commit()
        logger.info(f"已处理 {processed_count} 篇滞留的作文")
        
        # 更新任务状态
        update_task_status(task_id, "completed", result={
            "message": f"已处理 {processed_count} 篇滞留的作文",
            "processed_count": processed_count
        })
        
        return {
            "status": "success",
            "message": f"已处理 {processed_count} 篇滞留的作文",
            "processed_count": processed_count
        }
        
    except Exception as e:
        logger.error(f"处理作文状态检查失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 更新任务状态
        update_task_status(task_id, "failed", error=str(e))
        
        return {
            "status": "error",
            "message": str(e),
            "processed_count": 0
        }

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
    name='app.tasks.maintenance_tasks.check_correction_system_health',
    bind=True,
    max_retries=2,
    acks_late=True,
    queue='periodic'
)
def check_correction_system_health(self, max_stuck_time_minutes=30):
    """
    全面检查批改系统健康状况，自动修复识别到的问题
    
    该任务会检查所有可能卡住的作文状态（包括各种临时状态如CORRECTING、UPLOADING等），
    并根据不同情况采取修复措施，同时记录详细日志以便后续分析。
    
    Args:
        self: Celery任务实例
        max_stuck_time_minutes: 最长卡住时间（分钟），默认30分钟
        
    Returns:
        dict: 处理结果
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] 开始检查批改系统健康状况...")
    
    # 记录开始的任务状态
    try:
        if 'TaskStatus' in globals():
            task_status = TaskStatus.create_from_task(
                task_id=task_id,
                task_name='check_correction_system_health',
                args=f"[{max_stuck_time_minutes}]",
                worker_id=self.request.hostname
            )
            task_status.mark_as_started()
    except Exception as e:
        logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
    
    try:
        # 导入必要的库
        from datetime import datetime, timedelta
        from flask import has_app_context, current_app
        from app import create_app
        from celery.result import AsyncResult
        
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
        
        # 初始化CorrectionService
        from app.core.correction.correction_service import CorrectionService
        correction_service = CorrectionService()
        
        try:
            # 计算最长卡住时间点
            threshold_time = datetime.utcnow() - timedelta(minutes=max_stuck_time_minutes)
            
            # 记录开始检查
            logger.info(f"[{task_id}] 检查卡住的作文 (阈值: {max_stuck_time_minutes}分钟)")
            
            # 1. 检查"CORRECTING"状态卡住的作文
            stuck_correcting_essays = Essay.query.filter(
                Essay.status == EssayStatus.CORRECTING.value,
                Essay.updated_at < threshold_time,
                Essay.is_deleted == False
            ).all()
            
            # 2. 检查"PENDING"状态长时间未处理的作文
            long_pending_threshold = datetime.utcnow() - timedelta(hours=2)
            stuck_pending_essays = Essay.query.filter(
                Essay.status == EssayStatus.PENDING.value,
                Essay.updated_at < long_pending_threshold,
                Essay.is_deleted == False
            ).all()
            
            # 结果统计
            results = {
                "correcting_reset_count": 0,
                "correcting_resubmit_count": 0,
                "pending_resubmit_count": 0,
                "failed_count": 0,
                "task_cancelled_count": 0,
                "errors": []
            }
            
            # 处理"CORRECTING"状态卡住的作文
            for essay in stuck_correcting_essays:
                try:
                    stuck_time = datetime.utcnow() - essay.updated_at
                    logger.info(f"[{task_id}] 处理卡住的作文: ID={essay.id}, 状态={essay.status}, 卡住时间={stuck_time}")
                    
                    # 获取关联的批改记录
                    correction = Correction.query.filter_by(essay_id=essay.id).first()
                    
                    # 检查是否有任务ID
                    if correction and correction.task_id:
                        task_result = AsyncResult(correction.task_id)
                        task_state = task_result.state
                        
                        if task_state in ["PENDING", "STARTED", "RECEIVED"]:
                            logger.info(f"[{task_id}] 任务 {correction.task_id} 状态为 {task_state}，尝试撤销")
                            
                            # 尝试撤销任务
                            from celery.task.control import revoke
                            revoke(correction.task_id, terminate=True)
                            results["task_cancelled_count"] += 1
                            
                            # 重置状态
                            correction_service.transition_essay_state(
                                essay.id,
                                EssayStatus.CORRECTING.value,
                                EssayStatus.PENDING.value,
                                f"系统自动重置卡住的作文状态 (卡住{stuck_time})"
                            )
                            results["correcting_reset_count"] += 1
                        
                        elif task_state in ["FAILURE", "REVOKED"]:
                            logger.info(f"[{task_id}] 任务 {correction.task_id} 状态为 {task_state}，标记为失败")
                            
                            # 标记为失败
                            correction_service.transition_essay_state(
                                essay.id,
                                EssayStatus.CORRECTING.value,
                                EssayStatus.FAILED.value,
                                f"批改任务失败或被撤销 (状态: {task_state})"
                            )
                            results["failed_count"] += 1
                            
                        elif task_state == "SUCCESS":
                            logger.warning(f"[{task_id}] 任务 {correction.task_id} 状态为SUCCESS但作文状态仍为CORRECTING，标记为完成")
                            
                            # 标记为完成
                            correction_service.transition_essay_state(
                                essay.id,
                                EssayStatus.CORRECTING.value,
                                EssayStatus.COMPLETED.value
                            )
                    else:
                        # 没有任务ID或批改记录，重置状态
                        logger.info(f"[{task_id}] 作文 {essay.id} 没有有效的任务ID，重置状态")
                        
                        correction_service.transition_essay_state(
                            essay.id,
                            EssayStatus.CORRECTING.value,
                            EssayStatus.PENDING.value,
                            f"系统自动重置卡住的作文状态 (卡住{stuck_time})"
                        )
                        results["correcting_reset_count"] += 1
                    
                except Exception as e:
                    logger.error(f"[{task_id}] 处理卡住的作文 {essay.id} 时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                    results["errors"].append(f"处理作文{essay.id}错误: {str(e)}")
            
            # 处理"PENDING"状态长时间未处理的作文
            for essay in stuck_pending_essays:
                try:
                    pending_time = datetime.utcnow() - essay.updated_at
                    logger.info(f"[{task_id}] 处理长时间PENDING的作文: ID={essay.id}, 状态={essay.status}, 未处理时间={pending_time}")
                    
                    # 获取关联的批改记录
                    correction = Correction.query.filter_by(essay_id=essay.id).first()
                    
                    # 如果没有批改记录或任务ID，尝试重新提交
                    if not correction or not correction.task_id:
                        # 重新提交批改任务
                        from app.tasks.correction_tasks import process_essay_correction
                        
                        try:
                            # 提交新任务
                            new_task = process_essay_correction.apply_async(args=[essay.id], queue='correction')
                            logger.info(f"[{task_id}] 重新提交作文批改任务: {essay.id}, 新任务ID: {new_task.id}")
                            
                            # 更新批改记录的任务ID
                            if correction:
                                correction.task_id = new_task.id
                                db.session.commit()
                            
                            results["pending_resubmit_count"] += 1
                        except Exception as task_err:
                            logger.error(f"[{task_id}] 重新提交作文 {essay.id} 批改任务失败: {str(task_err)}")
                            results["errors"].append(f"重新提交任务{essay.id}错误: {str(task_err)}")
                    
                except Exception as e:
                    logger.error(f"[{task_id}] 处理长时间PENDING的作文 {essay.id} 时出错: {str(e)}")
                    logger.error(traceback.format_exc())
                    results["errors"].append(f"处理作文{essay.id}错误: {str(e)}")
            
            # 统计结果
            total_processed = results["correcting_reset_count"] + results["pending_resubmit_count"] + results["failed_count"]
            logger.info(f"[{task_id}] 批改系统健康检查完成，共处理 {total_processed} 个问题作文")
            
            if 'task_status' in locals():
                task_status.mark_as_success(result=results)
                
            return results
            
        finally:
            # 如果创建了应用上下文，确保弹出它
            if ctx:
                try:
                    ctx.pop()
                    logger.info("应用上下文已弹出")
                except Exception as ex:
                    logger.warning(f"弹出应用上下文时出错: {str(ex)}")
    
    except Exception as e:
        error_msg = f"批改系统健康检查失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=error_msg)
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"[{task_id}] 将在 60 秒后重试批改系统健康检查")
            self.retry(exc=e, countdown=60)
            
        return {"status": "error", "message": error_msg} 