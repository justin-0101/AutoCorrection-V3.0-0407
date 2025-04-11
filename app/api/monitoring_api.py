#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
监控API模块
提供监控数据查询和状态修复的HTTP API
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func, and_, or_
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.models.db import db
from app.tasks.monitoring_tasks import metrics_store, generate_system_report
from app.tasks.correction_tasks import check_and_fix_inconsistent_statuses
from celery.result import AsyncResult
from celery import current_app as celery_app

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建Blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')


@monitoring_bp.route('/status', methods=['GET'])
def get_system_status():
    """获取系统状态概览"""
    try:
        # 启动异步任务生成报告
        task = generate_system_report.apply_async()
        result = task.get(timeout=5)  # 等待最多5秒获取结果
        
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'data': result.get('report')
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '获取系统状态失败')
            }), 500
    
    except Exception as e:
        logger.exception(f"获取系统状态失败: {str(e)}")
        
        # 如果异步任务超时，尝试直接获取一些基本信息
        try:
            with db.session() as session:
                pending_count = session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.PENDING
                ).scalar()
                
                processing_count = session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.CORRECTING
                ).scalar()
                
                completed_count = session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.COMPLETED
                ).scalar()
                
                failed_count = session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.FAILED
                ).scalar()
                
                # 计算24小时内的统计数据
                last_day = datetime.now() - timedelta(days=1)
                daily_completed = session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.COMPLETED,
                    Essay.updated_at >= last_day
                ).scalar()
                
                daily_failed = session.query(func.count(Essay.id)).filter(
                    Essay.status == EssayStatus.FAILED,
                    Essay.updated_at >= last_day
                ).scalar()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'timestamp': datetime.now().isoformat(),
                        'summary': {
                            'essays_pending': pending_count,
                            'essays_processing': processing_count,
                            'essays_completed': completed_count,
                            'essays_failed': failed_count,
                            'daily_completed': daily_completed,
                            'daily_failed': daily_failed
                        },
                        'note': '详细报告生成超时，显示基本信息'
                    }
                })
        
        except Exception as inner_e:
            logger.exception(f"获取基本系统状态也失败: {str(inner_e)}")
            return jsonify({
                'success': False,
                'message': f'获取系统状态失败: {str(e)}'
            }), 500


@monitoring_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """获取系统监控指标"""
    # 从URL参数获取过滤条件
    metric_type = request.args.get('type')  # gauge, counter, histogram, event
    metric_name = request.args.get('name')  # 指标名称前缀
    
    try:
        # 获取所有指标
        all_metrics = metrics_store.get_all_metrics()
        
        # 根据类型过滤
        if metric_type:
            if metric_type == 'gauge':
                metrics = {k: v for k, v in all_metrics.get('gauges', {}).items()}
            elif metric_type == 'counter':
                metrics = {k: v for k, v in all_metrics.get('counters', {}).items()}
            elif metric_type == 'histogram':
                metrics = {k: v for k, v in all_metrics.get('histograms', {}).items()}
            elif metric_type == 'event':
                # 获取事件计数
                metrics = {k: v for k, v in all_metrics.get('events', {}).items()}
            else:
                metrics = all_metrics
        else:
            metrics = all_metrics
        
        # 根据名称前缀过滤
        if metric_name:
            if metric_type:
                metrics = {k: v for k, v in metrics.items() if k.startswith(metric_name)}
            else:
                # 过滤所有类型中的指定名称
                filtered_metrics = {}
                for type_name, type_metrics in all_metrics.items():
                    if isinstance(type_metrics, dict):
                        filtered_metrics[type_name] = {k: v for k, v in type_metrics.items() 
                                                     if k.startswith(metric_name)}
                    else:
                        filtered_metrics[type_name] = type_metrics
                metrics = filtered_metrics
        
        return jsonify({
            'success': True,
            'data': metrics
        })
    
    except Exception as e:
        logger.exception(f"获取监控指标失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取监控指标失败: {str(e)}'
        }), 500


@monitoring_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """获取系统告警"""
    from app.tasks.monitoring_tasks import alert_manager
    
    try:
        # 获取最近的告警
        limit = request.args.get('limit', 10, type=int)
        recent_alerts = alert_manager.get_recent_alerts(limit)
        
        return jsonify({
            'success': True,
            'data': recent_alerts
        })
    
    except Exception as e:
        logger.exception(f"获取告警信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取告警信息失败: {str(e)}'
        }), 500


@monitoring_bp.route('/events/<event_type>', methods=['GET'])
def get_events(event_type):
    """获取事件历史"""
    try:
        # 获取最近的事件
        limit = request.args.get('limit', 10, type=int)
        recent_events = metrics_store.get_recent_events(event_type, limit)
        
        return jsonify({
            'success': True,
            'data': recent_events
        })
    
    except Exception as e:
        logger.exception(f"获取事件历史失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取事件历史失败: {str(e)}'
        }), 500


@monitoring_bp.route('/tasks/active', methods=['GET'])
def get_active_tasks():
    """获取当前活跃的任务"""
    try:
        # 从数据库获取处于CORRECTING状态的作文和批改记录
        with db.session() as session:
            active_corrections = session.query(
                Correction.id, 
                Correction.essay_id, 
                Correction.task_id, 
                Correction.status, 
                Correction.started_at
            ).filter(
                Correction.status == CorrectionStatus.CORRECTING
            ).all()
            
            # 检查每个任务的状态
            result = []
            for correction in active_corrections:
                task_info = {
                    'correction_id': correction.id,
                    'essay_id': correction.essay_id,
                    'task_id': correction.task_id,
                    'status': correction.status.name,
                    'started_at': correction.started_at.isoformat() if correction.started_at else None,
                    'running_time': None,
                    'celery_task_status': 'UNKNOWN'
                }
                
                # 计算运行时间
                if correction.started_at:
                    delta = datetime.now() - correction.started_at
                    task_info['running_time'] = delta.total_seconds()
                
                # 获取Celery任务状态
                if correction.task_id:
                    async_result = AsyncResult(correction.task_id, app=celery_app)
                    task_info['celery_task_status'] = async_result.state
                
                result.append(task_info)
            
            return jsonify({
                'success': True,
                'count': len(result),
                'data': result
            })
    
    except Exception as e:
        logger.exception(f"获取活跃任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取活跃任务失败: {str(e)}'
        }), 500


@monitoring_bp.route('/essays/inconsistent', methods=['GET'])
def get_inconsistent_essays():
    """获取状态不一致的作文"""
    try:
        with db.session() as session:
            # 查询状态不一致的记录
            inconsistent_data = session.query(
                Essay.id, 
                Essay.title, 
                Essay.status, 
                Correction.id.label('correction_id'), 
                Correction.status.label('correction_status')
            ).join(
                Correction, Essay.id == Correction.essay_id
            ).filter(
                ((Essay.status == EssayStatus.CORRECTING) & 
                 (Correction.status != CorrectionStatus.CORRECTING)) |
                ((Essay.status != EssayStatus.CORRECTING) & 
                 (Correction.status == CorrectionStatus.CORRECTING))
            ).all()
            
            result = []
            for row in inconsistent_data:
                result.append({
                    'essay_id': row.id,
                    'title': row.title,
                    'essay_status': row.status.name,
                    'correction_id': row.correction_id,
                    'correction_status': row.correction_status.name
                })
            
            return jsonify({
                'success': True,
                'count': len(result),
                'data': result
            })
    
    except Exception as e:
        logger.exception(f"获取状态不一致的作文失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取状态不一致的作文失败: {str(e)}'
        }), 500


@monitoring_bp.route('/essays/stale', methods=['GET'])
def get_stale_essays():
    """获取滞留的作文任务"""
    try:
        # 设置滞留时间阈值，默认1小时
        hours = request.args.get('hours', 1, type=int)
        stale_time = datetime.now() - timedelta(hours=hours)
        
        with db.session() as session:
            # 查询处于CORRECTING状态且开始时间超过阈值的作文
            stale_data = session.query(
                Essay.id, 
                Essay.title, 
                Correction.id.label('correction_id'), 
                Correction.task_id,
                Correction.started_at
            ).join(
                Correction, Essay.id == Correction.essay_id
            ).filter(
                Essay.status == EssayStatus.CORRECTING,
                Correction.status == CorrectionStatus.CORRECTING,
                Correction.started_at < stale_time
            ).all()
            
            result = []
            for row in stale_data:
                task_status = 'UNKNOWN'
                if row.task_id:
                    async_result = AsyncResult(row.task_id, app=celery_app)
                    task_status = async_result.state
                
                delta = datetime.now() - row.started_at if row.started_at else None
                
                result.append({
                    'essay_id': row.id,
                    'title': row.title,
                    'correction_id': row.correction_id,
                    'task_id': row.task_id,
                    'started_at': row.started_at.isoformat() if row.started_at else None,
                    'running_time': delta.total_seconds() if delta else None,
                    'celery_task_status': task_status
                })
            
            return jsonify({
                'success': True,
                'count': len(result),
                'data': result
            })
    
    except Exception as e:
        logger.exception(f"获取滞留任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取滞留任务失败: {str(e)}'
        }), 500


@monitoring_bp.route('/fix/inconsistent', methods=['POST'])
def fix_inconsistent_essays():
    """修复状态不一致的作文"""
    try:
        # 可以选择性地传入特定作文ID，否则修复所有不一致的记录
        data = request.get_json() or {}
        essay_ids = data.get('essay_ids', [])
        
        # 调用异步任务修复不一致状态
        task = check_and_fix_inconsistent_statuses.apply_async()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': '已启动状态修复任务'
        })
    
    except Exception as e:
        logger.exception(f"启动状态修复任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'启动状态修复任务失败: {str(e)}'
        }), 500


@monitoring_bp.route('/fix/stale', methods=['POST'])
def fix_stale_essays():
    """修复滞留的作文任务"""
    try:
        data = request.get_json() or {}
        essay_ids = data.get('essay_ids', [])
        action = data.get('action', 'reset')  # reset, fail, retry
        
        if not essay_ids:
            return jsonify({
                'success': False,
                'message': '未提供作文ID'
            }), 400
        
        with db.session() as session:
            for essay_id in essay_ids:
                essay = session.query(Essay).get(essay_id)
                correction = session.query(Correction).filter_by(essay_id=essay_id).first()
                
                if not essay or not correction:
                    continue
                
                # 检查任务状态
                task_id = correction.task_id
                if task_id:
                    try:
                        # 尝试终止任务
                        async_result = AsyncResult(task_id, app=celery_app)
                        async_result.revoke(terminate=True)
                        logger.info(f"已终止任务 {task_id}")
                    except Exception as revoke_error:
                        logger.error(f"终止任务 {task_id} 失败: {str(revoke_error)}")
                
                try:
                    session.begin_nested()
                    
                    if action == 'reset':
                        # 重置为待处理状态
                        essay.status = EssayStatus.PENDING
                        correction.status = CorrectionStatus.PENDING
                        correction.task_id = None
                    elif action == 'fail':
                        # 标记为失败状态
                        essay.status = EssayStatus.FAILED
                        correction.status = CorrectionStatus.FAILED
                        if hasattr(correction, 'error_message'):
                            correction.error_message = "手动标记为失败"
                        elif hasattr(correction, 'error'):
                            correction.error = "手动标记为失败"
                    
                    session.commit()
                    logger.info(f"已更新作文 {essay_id} 的状态为 {action}")
                
                except Exception as update_error:
                    session.rollback()
                    logger.error(f"更新作文 {essay_id} 状态失败: {str(update_error)}")
                    return jsonify({
                        'success': False,
                        'message': f'更新作文状态失败: {str(update_error)}'
                    }), 500
            
            # 如果选择retry，提交新的批改任务
            if action == 'retry':
                from app.tasks.correction_tasks import process_essay_correction
                
                for essay_id in essay_ids:
                    try:
                        # 先将作文状态重置为PENDING
                        essay = session.query(Essay).get(essay_id)
                        correction = session.query(Correction).filter_by(essay_id=essay_id).first()
                        
                        if essay and correction:
                            session.begin_nested()
                            essay.status = EssayStatus.PENDING
                            correction.status = CorrectionStatus.PENDING
                            correction.task_id = None
                            session.commit()
                        
                        # 提交新任务
                        task = process_essay_correction.apply_async(args=[essay_id])
                        logger.info(f"已为作文 {essay_id} 重新提交批改任务 {task.id}")
                    
                    except Exception as retry_error:
                        session.rollback()
                        logger.error(f"为作文 {essay_id} 重新提交任务失败: {str(retry_error)}")
            
            return jsonify({
                'success': True,
                'message': f'已成功处理 {len(essay_ids)} 篇滞留作文'
            })
    
    except Exception as e:
        logger.exception(f"处理滞留作文失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理滞留作文失败: {str(e)}'
        }), 500


@monitoring_bp.route('/tasks/retry', methods=['POST'])
def retry_failed_tasks():
    """重试失败的任务"""
    try:
        data = request.get_json() or {}
        essay_ids = data.get('essay_ids', [])
        
        if not essay_ids:
            return jsonify({
                'success': False,
                'message': '未提供作文ID'
            }), 400
        
        from app.tasks.correction_tasks import process_essay_correction
        
        results = []
        with db.session() as session:
            for essay_id in essay_ids:
                try:
                    # 获取作文和批改记录
                    essay = session.query(Essay).get(essay_id)
                    correction = session.query(Correction).filter_by(essay_id=essay_id).first()
                    
                    if not essay or not correction:
                        results.append({
                            'essay_id': essay_id,
                            'success': False,
                            'message': '找不到作文或批改记录'
                        })
                        continue
                    
                    # 只允许重试FAILED状态的作文
                    if essay.status != EssayStatus.FAILED:
                        results.append({
                            'essay_id': essay_id,
                            'success': False,
                            'message': f'作文状态不是FAILED，当前状态: {essay.status.name}'
                        })
                        continue
                    
                    # 更新状态为PENDING
                    session.begin_nested()
                    essay.status = EssayStatus.PENDING
                    correction.status = CorrectionStatus.PENDING
                    correction.task_id = None
                    
                    # 清除错误信息
                    if hasattr(correction, 'error_message'):
                        correction.error_message = None
                    elif hasattr(correction, 'error'):
                        correction.error = None
                    
                    session.commit()
                    
                    # 提交新任务
                    task = process_essay_correction.apply_async(args=[essay_id])
                    
                    results.append({
                        'essay_id': essay_id,
                        'success': True,
                        'task_id': task.id,
                        'message': '已成功提交重试任务'
                    })
                    
                    logger.info(f"已为作文 {essay_id} 提交重试任务 {task.id}")
                
                except Exception as e:
                    session.rollback()
                    logger.error(f"为作文 {essay_id} 提交重试任务失败: {str(e)}")
                    results.append({
                        'essay_id': essay_id,
                        'success': False,
                        'message': f'提交重试任务失败: {str(e)}'
                    })
        
        # 计算成功和失败数量
        success_count = sum(1 for r in results if r['success'])
        fail_count = sum(1 for r in results if not r['success'])
        
        return jsonify({
            'success': True,
            'message': f'处理完成: {success_count} 成功, {fail_count} 失败',
            'results': results
        })
    
    except Exception as e:
        logger.exception(f"重试失败任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'重试失败任务失败: {str(e)}'
        }), 500 