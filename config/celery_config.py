"""
Celery配置模块
定义任务队列的各项配置
"""
import os
from datetime import timedelta

# 消息代理设置
broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# 序列化设置
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
enable_utc = True

# 任务设置
task_acks_late = True
task_reject_on_worker_lost = True
task_track_started = True
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 500

# 结果设置
result_expires = 60 * 60 * 24  # 1 day

# 配置任务队列
task_queues = {
    'default': {'exchange': 'default', 'routing_key': 'default'},
    'correction': {'exchange': 'correction', 'routing_key': 'correction.tasks'},
    'users': {'exchange': 'users', 'routing_key': 'user.tasks'}
}

# 默认队列
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'

# 任务路由
task_routes = {
    'app.tasks.correction_tasks.*': {'queue': 'correction'},
    'app.tasks.user_tasks.*': {'queue': 'users'},
}

# 定时任务
beat_schedule = {
    'reset-monthly-essay-count': {
        'task': 'app.tasks.user_tasks.reset_monthly_essay_count',
        'schedule': timedelta(days=1),  # 每天检查一次
        'options': {'queue': 'users'}
    }
}

# 工作进程配置
worker_pool_restarts = True  # 允许工作进程重启

# 将所有配置导出为一个字典
CELERY_CONFIG = {
    'broker_url': broker_url,
    'result_backend': result_backend,
    'task_serializer': task_serializer,
    'result_serializer': result_serializer,
    'accept_content': accept_content,
    'timezone': timezone,
    'enable_utc': enable_utc,
    'task_acks_late': task_acks_late,
    'task_reject_on_worker_lost': task_reject_on_worker_lost,
    'task_track_started': task_track_started,
    'worker_prefetch_multiplier': worker_prefetch_multiplier,
    'worker_max_tasks_per_child': worker_max_tasks_per_child,
    'result_expires': result_expires,
    'task_queues': task_queues,
    'task_default_queue': task_default_queue,
    'task_default_exchange': task_default_exchange,
    'task_default_routing_key': task_default_routing_key,
    'task_routes': task_routes,
    'beat_schedule': beat_schedule,
    'worker_pool_restarts': worker_pool_restarts,
} 