#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery配置文件
定义Celery任务队列的详细配置
"""

import os
import logging
from kombu import Queue, Exchange
from app.config import config
from datetime import timedelta

# 消息代理配置
broker_url = config.CELERY_CONFIG.get('broker_url', 'redis://localhost:6379/0')
result_backend = config.CELERY_CONFIG.get('result_backend', 'redis://localhost:6379/0')

# 任务序列化格式
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']

# 时区配置
timezone = 'Asia/Shanghai'
enable_utc = False

# 任务跟踪和结果配置
task_track_started = True
task_time_limit = 3600  # 任务执行时间限制，超过则被终止
task_soft_time_limit = 3000  # 软限制，触发异常但不终止任务
worker_max_tasks_per_child = 200  # worker子进程在自动重启前最多执行的任务数
worker_prefetch_multiplier = 4  # worker预取任务数量倍数

# 结果配置
result_expires = 3600  # 结果在backend中的过期时间(秒)

# 日志配置
worker_hijack_root_logger = False  # 不覆盖根日志器
worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"

# 任务默认配置
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'
task_default_delivery_mode = 'persistent'  # 消息持久化

# 定义交换机
task_exchanges = (
    # 默认交换机
    Exchange('default', type='direct'),
    # 优先级交换机
    Exchange('priority', type='direct'),
    # 死信交换机
    Exchange('dead_letter', type='topic'),
    # 批改交换机
    Exchange('correction', type='direct'),
    # 邮件交换机
    Exchange('email', type='direct'),
    # 备份交换机
    Exchange('backup', type='direct'),
    # 分析交换机
    Exchange('analytics', type='direct'),
    # 周期性任务交换机
    Exchange('periodic', type='direct'),
)

# 队列定义
task_queues = (
    # 默认队列 - 一般任务
    Queue(
        'default', 
        Exchange('default'), 
        routing_key='default',
        queue_arguments={'x-max-priority': 10}  # 支持优先级
    ),
    
    # 高优先级队列 - 重要任务
    Queue(
        'high', 
        Exchange('priority'), 
        routing_key='high',
        queue_arguments={
            'x-max-priority': 10,      # 支持优先级
            'x-message-ttl': 86400000, # 消息存活时间 24小时
        }
    ),
    
    # 低优先级队列 - 可延迟任务
    Queue(
        'low', 
        Exchange('priority'), 
        routing_key='low',
        queue_arguments={
            'x-max-priority': 5,      # 支持优先级，但级别较低
            'x-message-ttl': 259200000, # 消息存活时间 3天
        }
    ),
    
    # 作文批改队列
    Queue(
        'correction', 
        Exchange('correction'), 
        routing_key='correction',
        queue_arguments={
            'x-max-priority': 10,
            'x-message-ttl': 86400000, # 24小时
            # 当消息被拒绝或过期时，发送到死信队列
            'x-dead-letter-exchange': 'dead_letter',
            'x-dead-letter-routing-key': 'dlq.correction'
        }
    ),
    
    # 作文批改高优先级队列
    Queue(
        'correction.priority', 
        Exchange('correction'), 
        routing_key='correction.priority',
        queue_arguments={
            'x-max-priority': 10,
            'x-message-ttl': 43200000, # 12小时
            'x-dead-letter-exchange': 'dead_letter',
            'x-dead-letter-routing-key': 'dlq.correction'
        }
    ),
    
    # 邮件发送队列
    Queue(
        'email', 
        Exchange('email'), 
        routing_key='email',
        queue_arguments={
            'x-max-priority': 8,
            'x-message-ttl': 172800000, # 48小时
            'x-dead-letter-exchange': 'dead_letter',
            'x-dead-letter-routing-key': 'dlq.email'
        }
    ),
    
    # 定期任务队列
    Queue(
        'periodic', 
        Exchange('periodic'), 
        routing_key='periodic',
        queue_arguments={
            'x-max-priority': 5,
            'x-message-ttl': 86400000, # 24小时
            'x-dead-letter-exchange': 'dead_letter',
            'x-dead-letter-routing-key': 'dlq.periodic'
        }
    ),
    
    # 备份任务队列
    Queue(
        'backup', 
        Exchange('backup'), 
        routing_key='backup',
        queue_arguments={
            'x-max-priority': 3,
            'x-message-ttl': 604800000, # 7天
            'x-dead-letter-exchange': 'dead_letter',
            'x-dead-letter-routing-key': 'dlq.backup'
        }
    ),
    
    # 分析统计队列
    Queue(
        'analytics', 
        Exchange('analytics'), 
        routing_key='analytics',
        queue_arguments={
            'x-max-priority': 2,
            'x-message-ttl': 259200000, # 3天
            'x-dead-letter-exchange': 'dead_letter',
            'x-dead-letter-routing-key': 'dlq.analytics'
        }
    ),
    
    # 死信队列 - 按类型划分
    Queue(
        'dlq.correction', 
        Exchange('dead_letter'), 
        routing_key='dlq.correction'
    ),
    Queue(
        'dlq.email', 
        Exchange('dead_letter'), 
        routing_key='dlq.email'
    ),
    Queue(
        'dlq.periodic', 
        Exchange('dead_letter'), 
        routing_key='dlq.periodic'
    ),
    Queue(
        'dlq.default', 
        Exchange('dead_letter'), 
        routing_key='dlq.#'  # 捕获所有其他死信消息
    ),
)

# 任务路由配置
task_routes = {
    # 批改任务
    'app.tasks.correction_tasks.process_essay_correction': {'queue': 'correction'},
    'app.tasks.correction_tasks.high_priority_essay_correction': {'queue': 'correction.priority'},
    'app.tasks.correction_tasks.batch_process_essays': {'queue': 'correction'},
    
    # 邮件任务
    'app.tasks.notification_tasks.*': {'queue': 'email'},
    
    # 分析任务
    'app.tasks.analytics_tasks.*': {'queue': 'analytics'},
    
    # 备份任务
    'app.tasks.backup_tasks.*': {'queue': 'backup'},
    
    # 定期任务
    'app.tasks.scheduled_tasks.*': {'queue': 'periodic'},
    'app.tasks.correction_tasks.cleanup_stale_tasks': {'queue': 'periodic'},
}

# 定时任务相关配置
beat_scheduler = 'celery.beat.PersistentScheduler'
beat_schedule_filename = 'celerybeat-schedule'
beat_max_loop_interval = 300  # 调度器循环最大间隔(秒)

# Celery Beat 定时任务
beat_schedule = {
    # 定期处理失败任务的通知
    'process-failed-tasks-notification': {
        'task': 'app.tasks.notification_tasks.process_failed_tasks_notification',
        'schedule': timedelta(minutes=30),  # 每30分钟执行一次
        'options': {
            'queue': 'periodic',
            'expires': 600,  # 10分钟后过期
        },
    },
    
    # 清理长时间未完成的任务状态
    'cleanup-stale-task-statuses': {
        'task': 'app.tasks.maintenance_tasks.cleanup_stale_task_statuses',
        'schedule': timedelta(hours=12),  # 每12小时执行一次
        'options': {
            'queue': 'periodic',
            'expires': 3600,  # 1小时后过期
        },
    },
    
    # 更新任务队列长度指标
    'update-queue-length-metrics': {
        'task': 'app.tasks.monitoring_tasks.update_queue_length_metrics',
        'schedule': timedelta(minutes=5),  # 每5分钟执行一次
        'options': {
            'queue': 'periodic',
            'expires': 240,  # 4分钟后过期
        },
    },
    
    # 每日重新处理失败的作文批改任务
    'reprocess-failed-corrections': {
        'task': 'app.tasks.batch_processor_tasks.reprocess_failed_corrections',
        'schedule': timedelta(days=1),  # 每24小时执行一次
        'kwargs': {
            'time_range_days': 3,  # 处理最近3天内的失败作文
            'max_essays': 100,     # 最多处理100篇
            'batch_size': 20,      # 每批20篇
            'high_priority': False # 使用普通优先级
        },
        'options': {
            'queue': 'periodic',
            'expires': 7200,  # 2小时后过期
        },
    },
    
    # 每周清理旧的任务状态记录
    'cleanup-old-task-statuses': {
        'task': 'app.tasks.batch_processor_tasks.bulk_delete_old_data',
        'schedule': timedelta(days=7),  # 每周执行一次
        'kwargs': {
            'data_type': 'task_status',
            'days_to_keep': 30,    # 保留30天的数据
            'batch_size': 5000,    # 每批处理5000条记录
            'dry_run': False       # 实际执行删除操作
        },
        'options': {
            'queue': 'periodic',
            'expires': 7200,  # 2小时后过期
        },
    },
}

# Flower监控配置
flower_port = config.CELERY_CONFIG.get('flower_port', 5555)
flower_basic_auth = config.CELERY_CONFIG.get('flower_basic_auth', None)

# Worker进程池配置
worker_pool = 'prefork'  # 可选 prefork, eventlet, gevent
worker_concurrency = config.CELERY_CONFIG.get('worker_concurrency', 8)  # worker进程数

# 任务发送重试配置
task_publish_retry = True
task_publish_retry_policy = {
    'max_retries': 3,
    'interval_start': 0.2,
    'interval_step': 0.5,
    'interval_max': 3,
}

# 任务执行重试配置
task_acks_late = True  # 任务执行完成后再确认，可防止worker异常丢失任务
task_reject_on_worker_lost = True  # worker异常终止时，重新入队任务

# 任务优先级设置
task_inherit_parent_priority = True  # 子任务继承父任务的优先级
task_default_priority = 5           # 默认优先级 (1-10)

# 死信队列与任务持久化配置
task_queues_ha_policy = 'all'  # 高可用策略

# 消息代理连接设置
broker_connection_retry = True  # 连接失败时自动重试
broker_connection_retry_on_startup = True  # 启动时自动重试连接
broker_connection_max_retries = 10  # 最大重试次数
broker_connection_timeout = 4.0  # 连接超时时间(秒)
broker_heartbeat = 60  # 心跳检测间隔(秒)
broker_pool_limit = 20  # 连接池大小

# 死信队列处理配置
broker_transport_options = {
    'visibility_timeout': 43200,  # 12小时，防止任务被重复处理
    'max_priority': 10,           # 支持的最大优先级
    'queue_order_strategy': 'priority',  # 按优先级排序策略
    'fanout_prefix': True,        # 为广播交换机添加前缀
    'fanout_patterns': True,      # 支持广播模式的模式匹配
}

# Prometheus监控配置 
prometheus_metrics_enabled = os.environ.get('PROMETHEUS_METRICS_ENABLED', 'false').lower() == 'true'

# 初始化Prometheus指标和信号处理器
if prometheus_metrics_enabled:
    try:
        # 尝试导入Prometheus客户端库
        from prometheus_client import Counter, Histogram, Gauge
        from prometheus_client import start_http_server
        from celery.signals import (
            task_received, task_success, task_failure, 
            task_retry, task_revoked, task_rejected,
            worker_ready, worker_shutdown
        )
        
        # 创建度量指标
        TASK_SUCCEEDED = Counter(
            'celery_tasks_succeeded_total',
            'Total number of succeeded tasks',
            ['task_name', 'queue']
        )
        
        TASK_FAILED = Counter(
            'celery_tasks_failed_total',
            'Total number of failed tasks',
            ['task_name', 'queue']
        )
        
        TASK_RETRIED = Counter(
            'celery_tasks_retried_total',
            'Total number of retried tasks',
            ['task_name', 'queue']
        )
        
        TASK_RECEIVED = Counter(
            'celery_tasks_received_total',
            'Total number of received tasks',
            ['task_name', 'queue']
        )
        
        TASK_REVOKED = Counter(
            'celery_tasks_revoked_total',
            'Total number of revoked tasks',
            ['task_name', 'queue']
        )
        
        TASK_REJECTED = Counter(
            'celery_tasks_rejected_total',
            'Total number of rejected tasks',
            ['task_name', 'queue']
        )
        
        TASK_DURATION = Histogram(
            'celery_task_duration_seconds',
            'Task duration in seconds',
            ['task_name', 'queue'],
            buckets=(0.01, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
        )
        
        TASKS_ACTIVE = Gauge(
            'celery_tasks_active',
            'Number of active tasks',
            ['queue']
        )
        
        QUEUE_LENGTH = Gauge(
            'celery_queue_length',
            'Number of tasks in the queue',
            ['queue']
        )
        
        WORKER_ONLINE = Gauge(
            'celery_worker_online',
            'Number of workers online',
        )
        
        # 信号处理函数
        @task_received.connect
        def on_task_received(request, **kwargs):
            task_name = request.name or "unknown"
            queue = request.delivery_info.get('routing_key', 'unknown') if hasattr(request, 'delivery_info') else 'unknown'
            TASK_RECEIVED.labels(task_name=task_name, queue=queue).inc()
        
        @task_success.connect
        def on_task_success(sender, **kwargs):
            task_name = sender.name if hasattr(sender, 'name') else "unknown"
            queue = sender.request.delivery_info.get('routing_key', 'unknown') if hasattr(sender.request, 'delivery_info') else 'unknown'
            runtime = sender.request.runtime if hasattr(sender.request, 'runtime') else 0
            TASK_SUCCEEDED.labels(task_name=task_name, queue=queue).inc()
            TASK_DURATION.labels(task_name=task_name, queue=queue).observe(runtime)
        
        @task_failure.connect
        def on_task_failure(sender, task_id, exception, **kwargs):
            task_name = sender.name if hasattr(sender, 'name') else "unknown"
            queue = sender.request.delivery_info.get('routing_key', 'unknown') if hasattr(sender.request, 'delivery_info') else 'unknown'
            TASK_FAILED.labels(task_name=task_name, queue=queue).inc()
        
        @task_retry.connect
        def on_task_retry(sender, request, reason, **kwargs):
            task_name = sender.name if hasattr(sender, 'name') else "unknown"
            queue = request.delivery_info.get('routing_key', 'unknown') if hasattr(request, 'delivery_info') else 'unknown'
            TASK_RETRIED.labels(task_name=task_name, queue=queue).inc()
        
        @task_revoked.connect
        def on_task_revoked(sender, request, terminated, expired, **kwargs):
            task_name = sender.name if hasattr(sender, 'name') else "unknown"
            queue = request.delivery_info.get('routing_key', 'unknown') if hasattr(request, 'delivery_info') else 'unknown'
            TASK_REVOKED.labels(task_name=task_name, queue=queue).inc()
        
        @task_rejected.connect
        def on_task_rejected(sender, request, **kwargs):
            task_name = sender.name if hasattr(sender, 'name') else "unknown"
            queue = request.delivery_info.get('routing_key', 'unknown') if hasattr(request, 'delivery_info') else 'unknown'
            TASK_REJECTED.labels(task_name=task_name, queue=queue).inc()
        
        @worker_ready.connect
        def on_worker_ready(sender, **kwargs):
            WORKER_ONLINE.inc()
        
        @worker_shutdown.connect
        def on_worker_shutdown(sender, **kwargs):
            WORKER_ONLINE.dec()
        
        # 启动Prometheus HTTP服务器
        def start_prometheus_server():
            """启动Prometheus HTTP服务器以暴露监控指标"""
            try:
                prometheus_port = int(os.environ.get('PROMETHEUS_PORT', 9090))
                start_http_server(prometheus_port)
                logging.getLogger('app.tasks').info(f"Prometheus指标HTTP服务器已启动，端口: {prometheus_port}")
            except Exception as e:
                logging.getLogger('app.tasks').warning(f"无法启动Prometheus HTTP服务器: {str(e)}")
        
        # 不会自动调用，需要在worker启动时手动调用
        # 可以在celery worker启动参数中添加 --on-ready start_prometheus_server
        
    except ImportError:
        logging.getLogger('app.tasks').warning("无法导入prometheus_client模块，监控指标已禁用")

# 死信队列处理任务
def process_dead_letter_queues():
    """处理死信队列中的消息，通常由管理员触发或定期执行"""
    from celery import Celery
    from app.models.task_status import TaskStatus, TaskState
    
    app = Celery()
    app.config_from_object('app.tasks.celery_config')
    
    # 获取死信队列列表
    dlq_queues = [q.name for q in task_queues if q.name.startswith('dlq.')]
    
    results = {}
    for queue in dlq_queues:
        # 检查队列中的消息
        try:
            # 此处需要使用底层API检查队列
            # 为简化示例，这里使用模拟代码
            messages_count = 0  # 实际实现需要通过broker API获取
            
            results[queue] = {
                'queue': queue,
                'messages': messages_count,
                'processed': 0,
                'failed': 0
            }
            
            # 处理死信队列消息的逻辑将根据业务需求实现
            # 例如记录到日志、通知管理员、尝试重新处理等
            
        except Exception as e:
            results[queue] = {
                'queue': queue,
                'error': str(e)
            }
    
    return results
