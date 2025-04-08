#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
监控任务模块
提供系统监控相关的任务，包括指标更新、健康检查等
"""

import logging
import redis
import json
from app.tasks.celery_app import celery_app
from app.tasks.logging_config import get_task_logger
from app.models.task_status import TaskStatus, TaskState
from app.models.db import db
from app.config import config

# 获取任务专用日志记录器
logger = get_task_logger()

@celery_app.task(
    name='app.tasks.monitoring_tasks.update_queue_length_metrics',
    bind=True,
    max_retries=2,
    queue='periodic'
)
def update_queue_length_metrics(self):
    """
    更新队列长度指标
    
    Args:
        self: Celery任务实例
        
    Returns:
        dict: 处理结果
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] 开始更新队列长度指标")
    
    # 记录任务状态
    try:
        task_status = TaskStatus.create_from_task(
            task_id=task_id,
            task_name='update_queue_length_metrics',
            worker_id=self.request.hostname
        )
        task_status.mark_as_started()
    except Exception as e:
        logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
    
    try:
        # 连接到Redis
        broker_url = config.CELERY_CONFIG.get('broker_url', 'redis://localhost:6379/0')
        
        # 分析URL获取主机、端口、密码和数据库信息
        if broker_url.startswith('redis://'):
            # 格式: redis://[:password@]host[:port][/db]
            url_parts = broker_url.replace('redis://', '').split('@')
            if len(url_parts) > 1:
                password = url_parts[0]
                host_port_db = url_parts[1]
            else:
                password = None
                host_port_db = url_parts[0]
            
            host_port, *db_parts = host_port_db.split('/')
            db = int(db_parts[0]) if db_parts else 0
            
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 6379
                
            redis_client = redis.Redis(
                host=host, 
                port=port, 
                password=password, 
                db=db,
                socket_timeout=5.0
            )
        else:
            # 不支持的URL格式
            logger.error(f"[{task_id}] 不支持的broker URL格式: {broker_url}")
            return {
                'status': 'error',
                'message': f'不支持的broker URL格式: {broker_url}',
                'task_id': task_id
            }
        
        # 定义要检查的队列列表
        queues = [
            'default', 'high', 'low', 'correction', 'correction.priority',
            'email', 'periodic', 'backup', 'analytics', 
            'dlq.correction', 'dlq.email', 'dlq.periodic', 'dlq.default'
        ]
        
        # 获取队列长度并更新指标
        queue_lengths = {}
        
        for queue in queues:
            # Celery默认在Redis中使用key格式: celery + queue name
            queue_key = f'celery:{queue}'
            
            try:
                # 对于Redis，使用LLEN获取列表长度
                queue_length = redis_client.llen(queue_key)
                queue_lengths[queue] = queue_length
                
                # 如果启用了Prometheus监控，则更新指标
                if config.TASK_CONFIG.get('prometheus_metrics_enabled', False):
                    try:
                        from prometheus_client import Gauge
                        QUEUE_LENGTH = Gauge(
                            'celery_queue_length',
                            'Number of tasks in the queue',
                            ['queue']
                        )
                        QUEUE_LENGTH.labels(queue=queue).set(queue_length)
                    except (ImportError, Exception) as e:
                        logger.warning(f"[{task_id}] 无法更新Prometheus指标: {str(e)}")
                
                logger.debug(f"[{task_id}] 队列 '{queue}' 当前长度: {queue_length}")
                
            except Exception as queue_error:
                logger.warning(f"[{task_id}] 获取队列 '{queue}' 长度失败: {str(queue_error)}")
                queue_lengths[queue] = -1  # 表示获取失败
        
        # 关闭Redis连接
        redis_client.close()
        
        # 计算活跃任务数量
        active_tasks_count = TaskStatus.query.filter(
            TaskStatus.status.in_([TaskState.STARTED, TaskState.RECEIVED, TaskState.RETRY])
        ).count()
        
        # 更新活跃任务数量指标
        if config.TASK_CONFIG.get('prometheus_metrics_enabled', False):
            try:
                from prometheus_client import Gauge
                TASKS_ACTIVE = Gauge(
                    'celery_tasks_active',
                    'Number of active tasks'
                )
                TASKS_ACTIVE.set(active_tasks_count)
            except (ImportError, Exception) as e:
                logger.warning(f"[{task_id}] 无法更新活跃任务指标: {str(e)}")
        
        # 结果数据
        result = {
            'status': 'success',
            'queues': queue_lengths,
            'active_tasks': active_tasks_count,
            'task_id': task_id,
            'timestamp': str(db.func.now())
        }
        
        # 更新任务状态
        if 'task_status' in locals():
            task_status.mark_as_success(result=result)
        
        logger.info(f"[{task_id}] 队列长度指标更新完成")
        return result
        
    except Exception as e:
        logger.error(f"[{task_id}] 更新队列长度指标失败: {str(e)}")
        
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=str(e))
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"[{task_id}] 将在 60 秒后重试更新队列长度指标")
            self.retry(exc=e, countdown=60)
            
        return {
            'status': 'error',
            'message': str(e),
            'task_id': task_id
        }


@celery_app.task(
    name='app.tasks.monitoring_tasks.perform_system_health_check',
    bind=True,
    queue='periodic'
)
def perform_system_health_check(self):
    """
    执行系统健康检查
    
    Args:
        self: Celery任务实例
        
    Returns:
        dict: 健康检查结果
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] 开始执行系统健康检查")
    
    # 记录任务状态
    try:
        task_status = TaskStatus.create_from_task(
            task_id=task_id,
            task_name='perform_system_health_check',
            worker_id=self.request.hostname
        )
        task_status.mark_as_started()
    except Exception as e:
        logger.warning(f"[{task_id}] 记录任务状态失败: {str(e)}")
    
    try:
        # 检查数据库连接
        db_status = 'ok'
        db_error = None
        
        try:
            # 尝试执行简单查询
            db.session.execute("SELECT 1").fetchall()
        except Exception as db_e:
            db_status = 'error'
            db_error = str(db_e)
            logger.error(f"[{task_id}] 数据库连接检查失败: {db_error}")
        
        # 检查Redis连接
        redis_status = 'ok'
        redis_error = None
        
        try:
            broker_url = config.CELERY_CONFIG.get('broker_url', 'redis://localhost:6379/0')
            
            # 分析URL获取Redis连接信息
            if broker_url.startswith('redis://'):
                url_parts = broker_url.replace('redis://', '').split('@')
                if len(url_parts) > 1:
                    password = url_parts[0]
                    host_port_db = url_parts[1]
                else:
                    password = None
                    host_port_db = url_parts[0]
                
                host_port, *db_parts = host_port_db.split('/')
                db = int(db_parts[0]) if db_parts else 0
                
                if ':' in host_port:
                    host, port = host_port.split(':')
                    port = int(port)
                else:
                    host = host_port
                    port = 6379
                    
                redis_client = redis.Redis(
                    host=host, 
                    port=port, 
                    password=password, 
                    db=db,
                    socket_timeout=3.0
                )
                
                # 测试连接
                redis_client.ping()
                redis_client.close()
            else:
                redis_status = 'error'
                redis_error = f'不支持的broker URL格式: {broker_url}'
        except Exception as redis_e:
            redis_status = 'error'
            redis_error = str(redis_e)
            logger.error(f"[{task_id}] Redis连接检查失败: {redis_error}")
        
        # 检查Celery Worker状态
        worker_status = 'ok'
        worker_error = None
        
        try:
            # 尝试执行简单的Celery任务检查
            # 此处可以使用i.app.control.inspect()获取worker信息
            # 简化起见，这里只检查是否有活跃任务
            active_tasks = TaskStatus.query.filter(
                TaskStatus.status.in_([TaskState.STARTED, TaskState.RECEIVED])
            ).count()
            
            workers_count = TaskStatus.query.with_entities(
                TaskStatus.worker_id
            ).filter(
                TaskStatus.status == TaskState.STARTED,
                TaskStatus.updated_at > db.func.date_sub(db.func.now(), db.text('INTERVAL 10 MINUTE'))
            ).distinct().count()
            
            if workers_count == 0:
                worker_status = 'warning'
                worker_error = '过去10分钟内没有活跃的worker'
                logger.warning(f"[{task_id}] {worker_error}")
        except Exception as worker_e:
            worker_status = 'error'
            worker_error = str(worker_e)
            logger.error(f"[{task_id}] Celery Worker检查失败: {worker_error}")
        
        # 汇总健康检查结果
        health_result = {
            'database': {
                'status': db_status,
                'error': db_error
            },
            'redis': {
                'status': redis_status,
                'error': redis_error
            },
            'celery_worker': {
                'status': worker_status,
                'error': worker_error,
                'active_tasks': active_tasks if 'active_tasks' in locals() else None,
                'workers_count': workers_count if 'workers_count' in locals() else None
            },
            'timestamp': str(db.func.now())
        }
        
        # 如果任意组件不是"ok"状态，则整体状态为最严重的状态
        overall_status = 'ok'
        if 'error' in [db_status, redis_status, worker_status]:
            overall_status = 'error'
        elif 'warning' in [db_status, redis_status, worker_status]:
            overall_status = 'warning'
        
        health_result['overall_status'] = overall_status
        
        # 记录健康检查结果
        logger.info(f"[{task_id}] 系统健康检查完成，状态: {overall_status}")
        
        # 如果状态为warning或error，记录警告信息
        if overall_status in ['warning', 'error']:
            logger.warning(f"[{task_id}] 系统健康检查发现问题: {json.dumps(health_result)}")
        
        # 更新任务状态
        if 'task_status' in locals():
            task_status.mark_as_success(result=health_result)
        
        return {
            'status': 'success',
            'health': health_result,
            'task_id': task_id
        }
        
    except Exception as e:
        logger.error(f"[{task_id}] 系统健康检查失败: {str(e)}")
        
        if 'task_status' in locals():
            task_status.mark_as_failure(error_message=str(e))
            
        return {
            'status': 'error',
            'message': str(e),
            'task_id': task_id
        } 