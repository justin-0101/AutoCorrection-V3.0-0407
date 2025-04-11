#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery配置文件
提供Celery任务队列的配置选项
"""

import os
import logging
from celery.schedules import timedelta

logger = logging.getLogger(__name__)

# Broker设置
broker_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
result_backend = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# 序列化设置
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'

# 任务结果设置
task_ignore_result = False

# 时区设置
timezone = 'Asia/Shanghai'
enable_utc = False

# Windows系统特定设置
worker_pool = 'solo'  # 在Windows上更可靠
worker_concurrency = 1  # 默认只使用一个工作进程

# 自动发现任务模块
imports = [
    'app.tasks.correction_tasks',
    'app.tasks.user_tasks',
    'app.tasks.subscription_tasks',
    'app.tasks.backup_tasks',
    'app.tasks.analytics_tasks',
    'app.tasks.notification_tasks',
    'app.tasks.monitoring_tasks'
]

# 队列配置
task_queues = {
    'celery': {
        'exchange': 'celery',
        'exchange_type': 'direct',
        'binding_key': 'celery',
    },
    'correction': {
        'exchange': 'correction',
        'exchange_type': 'direct',
        'binding_key': 'correction',
    },
    'correction.priority': {
        'exchange': 'correction',
        'exchange_type': 'direct',
        'binding_key': 'correction.priority',
    },
    'monitoring': {
        'exchange': 'monitoring',
        'exchange_type': 'direct',
        'binding_key': 'monitoring',
    }
}

# 路由配置
task_routes = {
    'app.tasks.correction_tasks.process_essay_correction': {'queue': 'correction'},
    'app.tasks.correction_tasks.high_priority_essay_correction': {'queue': 'correction.priority'},
    'app.tasks.correction_tasks.batch_process_essays': {'queue': 'correction'},
    'app.tasks.monitoring_tasks.*': {'queue': 'monitoring'},
}

# 全局任务设置
task_default_queue = 'celery'
task_default_exchange = 'celery'
task_default_exchange_type = 'direct'
task_default_routing_key = 'celery'

# 任务执行设置
task_acks_late = True
task_reject_on_worker_lost = True
task_time_limit = 600  # 10分钟
task_soft_time_limit = 300  # 5分钟

# 重试设置
task_default_retry_delay = 60  # 默认60秒后重试
task_max_retries = 3  # 默认最多重试3次

# 测试环境使用同步模式
if os.environ.get('FLASK_ENV') == 'testing':
    task_always_eager = True
    task_eager_propagates = True
    logger.info("测试环境：Celery使用同步执行模式")
else:
    task_always_eager = False

# 定时任务配置
beat_schedule = {
    'collect_system_metrics': {
        'task': 'app.tasks.monitoring_tasks.collect_system_metrics',
        'schedule': 60.0,  # 每分钟收集一次系统指标
        'options': {'queue': 'monitoring'}
    },
    'check_stale_tasks': {
        'task': 'app.tasks.monitoring_tasks.check_stale_tasks',
        'schedule': 300.0,  # 每5分钟检查一次滞留任务
        'options': {'queue': 'monitoring'}
    },
    'generate_system_report': {
        'task': 'app.tasks.monitoring_tasks.generate_system_report',
        'schedule': 3600.0,  # 每小时生成一次系统报告
        'options': {'queue': 'monitoring'}
    },
    'cleanup_metrics_store': {
        'task': 'app.tasks.monitoring_tasks.cleanup_metrics_store',
        'schedule': 86400.0,  # 每天清理一次指标存储
        'options': {'queue': 'monitoring'}
    },
    'status_consistency_check': {
        'task': 'app.tasks.correction_tasks.schedule_status_consistency_check',
        'schedule': 900.0,  # 每15分钟检查一次状态一致性
        'options': {'queue': 'monitoring'}
    }
} 