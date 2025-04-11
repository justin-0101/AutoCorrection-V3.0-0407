#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
监控任务模块
定义与监控、告警和统计相关的Celery任务
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from sqlalchemy import func, and_, or_
from celery import shared_task
from celery.signals import task_prerun, task_postrun, task_failure, task_success, worker_ready, task_retry
from celery.utils.log import get_task_logger

from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.models.db import db
from app.core.monitoring import metrics_store, alert_manager

# 创建日志记录器
logger = get_task_logger(__name__)

@shared_task
def update_queue_length_metrics():
    """
    更新任务队列长度指标
    
    收集并记录Celery任务队列的长度
    """
    try:
        from app.tasks.celery_app import celery_app
        
        # 获取队列信息
        active_queues = celery_app.control.inspect().active_queues()
        if not active_queues:
            logger.warning("无法获取队列信息")
            return {"status": "error", "message": "无法获取队列信息"}
        
        queue_lengths = {}
        for worker, queues in active_queues.items():
            for queue in queues:
                queue_name = queue.get('name', 'unknown')
                # 尝试获取队列长度
                try:
                    length = celery_app.control.inspect().scheduled().get(worker, [])
                    length = len(length)
                except:
                    length = 0
                
                if queue_name not in queue_lengths:
                    queue_lengths[queue_name] = 0
                queue_lengths[queue_name] += length
                
                # 记录队列长度
                metrics_store.set_gauge(f"tasks.queue_length", length, {"queue": queue_name})
        
        logger.info(f"队列长度指标更新完成: {queue_lengths}")
        return {
            "status": "success",
            "queue_lengths": queue_lengths
        }
    except Exception as e:
        logger.exception(f"更新队列长度指标失败: {str(e)}")
        return {
            "status": "error",
            "message": f"更新队列长度指标失败: {str(e)}"
        }

@worker_ready.connect
def initialize_monitoring(**kwargs):
    """在Celery worker启动时初始化监控系统"""
    logger.info("任务状态跟踪信号处理器已初始化")

# 任务运行前记录
@task_prerun.connect
def task_prerun_handler(task_id=None, task=None, args=None, kwargs=None, **_):
    """记录任务开始执行"""
    task_name = task.name if task else "unknown"
    
    # 记录任务开始
    metrics_store.increment_counter("tasks.started", 1, {"task": task_name})
    metrics_store.set_gauge("tasks.last_started_time", time.time(), {"task": task_name})
    
    # 特别记录作文批改任务
    if task_name == "app.tasks.correction_tasks.process_essay_correction" and args:
        essay_id = args[0] if args else None
        if essay_id:
            metrics_store.record_event("essay_correction.started", {
                "task_id": task_id,
                "essay_id": essay_id,
                "time": datetime.now().isoformat()
            })

# 任务成功完成记录
@task_success.connect
def task_success_handler(sender=None, result=None, **_):
    """记录任务成功完成"""
    task_name = sender.name if sender else "unknown"
    
    # 记录任务成功
    metrics_store.increment_counter("tasks.successes", 1, {"task": task_name})
    
    # 特别记录作文批改任务
    if task_name == "app.tasks.correction_tasks.process_essay_correction" and result:
        essay_id = result.get("essay_id")
        if essay_id:
            metrics_store.record_event("essay_correction.completed", {
                "essay_id": essay_id,
                "time": datetime.now().isoformat(),
                "status": "success"
            })
            
            # 记录处理时间
            if "processing_time" in result:
                metrics_store.record_histogram("essay_correction.duration", 
                                             result["processing_time"],
                                             {"status": "success"})

# 任务重试记录
@task_retry.connect
def task_retry_handler(sender=None, request=None, reason=None, **_):
    """记录任务重试"""
    task_name = sender.name if sender else "unknown"
    
    # 记录任务重试
    metrics_store.increment_counter("tasks.retries", 1, {"task": task_name})
    
    # 记录重试原因
    metrics_store.record_event("tasks.retry", {
        "task": task_name,
        "reason": str(reason)[:200] if reason else "Unknown reason",
        "time": datetime.now().isoformat()
    })

# 任务失败记录
@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, **_):
    """记录任务失败"""
    task_name = sender.name if sender else "unknown"
    
    # 记录任务失败
    metrics_store.increment_counter("tasks.failures", 1, {"task": task_name})
    
    # 记录作文批改任务失败
    if task_name == "app.tasks.correction_tasks.process_essay_correction" and args:
        essay_id = args[0] if args else None
        if essay_id:
            metrics_store.record_event("essay_correction.error", {
                "task_id": task_id,
                "essay_id": essay_id,
                "error": str(exception)[:200] if exception else "Unknown error",
                "time": datetime.now().isoformat()
            })
            
            # 增加失败计数
            metrics_store.increment_counter("essay_correction.failed", 1)
            
            # 如果有异常记录到指标
            if exception:
                error_type = type(exception).__name__
                metrics_store.increment_counter("essay_correction.errors", 1, 
                                              {"error_type": error_type})

# 任务完成记录（无论成功失败）
@task_postrun.connect
def task_postrun_handler(task_id=None, task=None, retval=None, state=None, **_):
    """记录任务完成（成功或失败）"""
    task_name = task.name if task else "unknown"
    
    # 记录任务完成
    metrics_store.increment_counter("tasks.completed", 1, {"task": task_name, "state": state})
    
    # 更新任务计数
    if task_name == "app.tasks.correction_tasks.process_essay_correction":
        metrics_store.increment_counter("essay_correction.total", 1)
        
        # 更新状态计数
        if state:
            metrics_store.increment_counter(f"essay_correction.state.{state.lower()}", 1)

@shared_task
def collect_system_metrics():
    """
    收集系统级别的指标
    
    收集当前系统状态的各种指标，如处理中的作文数、队列中的任务数等
    """
    try:
        with db.session() as session:
            # 统计各状态的作文数量
            essay_stats = {}
            for status in EssayStatus:
                count = session.query(func.count(Essay.id)).filter(Essay.status == status).scalar()
                essay_stats[status.name] = count
                metrics_store.set_gauge(f"essays.count.{status.name.lower()}", count)
            
            # 统计各状态的批改记录数量
            correction_stats = {}
            for status in CorrectionStatus:
                count = session.query(func.count(Correction.id)).filter(Correction.status == status).scalar()
                correction_stats[status.name] = count
                metrics_store.set_gauge(f"corrections.count.{status.name.lower()}", count)
            
            # 计算当前处理中的任务数
            processing_count = essay_stats.get(EssayStatus.CORRECTING.name, 0)
            metrics_store.set_gauge("essay_correction.processing", processing_count)
            
            # 计算失败率
            total_processed = (essay_stats.get(EssayStatus.COMPLETED.name, 0) + 
                              essay_stats.get(EssayStatus.FAILED.name, 0))
            if total_processed > 0:
                failure_rate = (essay_stats.get(EssayStatus.FAILED.name, 0) / total_processed) * 100
                metrics_store.set_gauge("essay_correction.failure_rate", failure_rate)
            
            # 记录状态不一致的数量
            inconsistent_count = session.query(func.count()).select_from(
                session.query(Essay, Correction).join(
                    Correction, Essay.id == Correction.essay_id
                ).filter(
                    ((Essay.status == EssayStatus.CORRECTING) & 
                     (Correction.status != CorrectionStatus.CORRECTING)) |
                    ((Essay.status != EssayStatus.CORRECTING) & 
                     (Correction.status == CorrectionStatus.CORRECTING))
                ).subquery()
            ).scalar()
            
            metrics_store.set_gauge("essays.inconsistent_status_count", inconsistent_count)
            
            # 如果不一致数量大于0，记录一个事件
            if inconsistent_count > 0:
                metrics_store.record_event("essays.inconsistent_status", {
                    "count": inconsistent_count,
                    "time": datetime.now().isoformat()
                })
            
            # 记录滞留任务数量（超过1小时仍处于处理中状态）
            stale_time = datetime.now() - timedelta(hours=1)
            stale_count = session.query(func.count(Correction.id)).filter(
                Correction.status == CorrectionStatus.CORRECTING,
                Correction.started_at < stale_time
            ).scalar()
            
            metrics_store.set_gauge("essay_correction.stale_tasks", stale_count)
            
            # 如果有滞留任务，记录事件
            if stale_count > 0:
                metrics_store.record_event("essay_correction.stale_tasks", {
                    "count": stale_count,
                    "time": datetime.now().isoformat()
                })
            
            # 获取今天的统计数据
            last_day = datetime.now() - timedelta(days=1)
            daily_stats = {
                "total": session.query(func.count(Essay.id)).filter(
                    Essay.updated_at >= last_day
                ).scalar(),
                "completed": session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.COMPLETED,
                    Essay.updated_at >= last_day
                ).scalar(),
                "failed": session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.FAILED,
                    Essay.updated_at >= last_day
                ).scalar()
            }
            
            metrics_store.set_gauge("essay_correction.daily.total", daily_stats["total"])
            metrics_store.set_gauge("essay_correction.daily.completed", daily_stats["completed"])
            metrics_store.set_gauge("essay_correction.daily.failed", daily_stats["failed"])
        
        logger.info(f"系统指标收集完成: 处理中作文={processing_count}, 状态不一致={inconsistent_count}, 滞留任务={stale_count}")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "essays": essay_stats,
                "corrections": correction_stats,
                "inconsistent_count": inconsistent_count,
                "stale_count": stale_count,
                "daily_stats": daily_stats
            }
        }
    
    except Exception as e:
        logger.exception(f"收集系统指标失败: {str(e)}")
        return {
            "status": "error",
            "message": f"收集系统指标失败: {str(e)}"
        }

@shared_task
def check_stale_tasks():
    """
    检查长时间未完成的任务
    
    检查并处理那些长时间处于CORRECTING状态但没有进展的任务
    """
    try:
        # 检查告警
        alerts = alert_manager.check_alerts()
        
        # 记录指标
        metrics_store.increment_counter("monitoring.stale_task_checks", 1)
        if alerts:
            metrics_store.record_event("monitoring.alerts", {
                "count": len(alerts),
                "alerts": alerts,
                "time": datetime.now().isoformat()
            })
        
        logger.info(f"滞留任务检查完成，发现 {len(alerts)} 个告警")
        
        return {
            "status": "success",
            "alerts": alerts,
            "message": f"检查完成，发现 {len(alerts)} 个告警"
        }
    except Exception as e:
        logger.exception(f"检查滞留任务失败: {str(e)}")
        metrics_store.increment_counter("monitoring.stale_task_check_errors", 1)
        
        return {
            "status": "error",
            "message": f"检查滞留任务失败: {str(e)}"
        }

@shared_task
def generate_system_report():
    """
    生成系统状态报告
    
    收集并整理系统各项指标，生成综合报告
    """
    try:
        # 获取所有指标
        all_metrics = metrics_store.get_all_metrics()
        
        # 获取最近的告警
        recent_alerts = alert_manager.get_recent_alerts()
        
        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": all_metrics,
            "alerts": recent_alerts
        }
        
        # 记录事件
        metrics_store.record_event("system.report", {
            "time": report["timestamp"],
            "metrics_count": len(all_metrics["gauges"]) + len(all_metrics["counters"]),
            "alerts_count": len(recent_alerts)
        })
        
        logger.info("系统报告生成完成")
        
        return {
            "status": "success",
            "report": report
        }
    except Exception as e:
        logger.exception(f"生成系统报告失败: {str(e)}")
        return {
            "status": "error",
            "message": f"生成系统报告失败: {str(e)}"
        }

@shared_task
def cleanup_metrics_store():
    """
    清理过旧的指标数据
    
    清理指标存储中的过旧数据，防止内存占用过大
    """
    try:
        # MetricsStore使用deque自动限制历史记录数量，无需手动清理
        logger.info("清理过旧指标数据完成")
        return {"status": "success", "message": "清理过旧指标数据完成"}
    except Exception as e:
        logger.exception(f"清理指标数据失败: {str(e)}")
        return {
            "status": "error",
            "message": f"清理指标数据失败: {str(e)}"
        }

@shared_task
def perform_system_health_check():
    """
    执行系统健康检查
    
    检查各项系统组件的健康状态，如数据库连接、Redis连接等
    
    Returns:
        Dict: 健康检查结果
    """
    try:
        results = {}
        # 检查数据库连接
        try:
            with db.session() as session:
                # 执行简单查询验证数据库连接
                session.execute("SELECT 1").scalar()
                results["database"] = {
                    "status": "healthy",
                    "message": "数据库连接正常"
                }
        except Exception as e:
            results["database"] = {
                "status": "unhealthy",
                "message": f"数据库连接异常: {str(e)}"
            }
            
        # 检查Redis连接
        try:
            from app.core.services.container import container
            redis_service = container.get("redis_service")
            if redis_service and redis_service.ping():
                results["redis"] = {
                    "status": "healthy",
                    "message": "Redis连接正常"
                }
            else:
                results["redis"] = {
                    "status": "warning",
                    "message": "Redis服务不可用或未配置"
                }
        except Exception as e:
            results["redis"] = {
                "status": "unhealthy",
                "message": f"Redis连接异常: {str(e)}"
            }
            
        # 检查AI服务
        try:
            from app.core.services.container import container
            ai_factory = container.get("ai_client_factory")
            if ai_factory:
                results["ai_service"] = {
                    "status": "healthy",
                    "message": "AI服务配置正常"
                }
            else:
                results["ai_service"] = {
                    "status": "warning",
                    "message": "AI服务未配置"
                }
        except Exception as e:
            results["ai_service"] = {
                "status": "unhealthy",
                "message": f"AI服务异常: {str(e)}"
            }
        
        # 确定整体状态
        if all(r["status"] == "healthy" for r in results.values()):
            overall_status = "healthy"
        elif any(r["status"] == "unhealthy" for r in results.values()):
            overall_status = "unhealthy"
        else:
            overall_status = "warning"
            
        logger.info(f"系统健康检查完成，状态: {overall_status}")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "components": results
        }
    except Exception as e:
        logger.exception(f"系统健康检查失败: {str(e)}")
        return {
            "status": "error",
            "message": f"健康检查失败: {str(e)}"
        } 