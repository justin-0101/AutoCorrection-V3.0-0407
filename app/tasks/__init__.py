#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务包初始化模块
导入和注册任务相关模块
"""

import logging

# 初始化日志
logger = logging.getLogger(__name__)

# 导入信号处理器并注册
try:
    from app.tasks.signal_handlers import register_signal_handlers
    register_signal_handlers()
    logger.info("任务状态跟踪信号处理器已初始化")
except Exception as e:
    logger.warning(f"初始化任务状态跟踪信号处理器时发生错误: {str(e)}")

# 导入任务模块，使celery能够发现这些任务
from app.tasks.celery_app import celery_app
from app.tasks.correction_tasks import (
    process_essay_correction,
    batch_process_essays,
    high_priority_essay_correction
)
from app.tasks.user_tasks import (
    send_notification_email,
    send_verification_code,
    process_user_activity,
    cleanup_inactive_users
)
from app.tasks.subscription_tasks import (
    process_subscription_task,
    renew_expiring_subscriptions
)
from app.tasks.backup_tasks import (
    backup_database,
    restore_database,
    list_backups
)
from app.tasks.analytics_tasks import (
    generate_daily_stats,
    generate_monthly_report,
    generate_user_progress_report
)
from app.tasks.notification_tasks import (
    send_task_failure_notification,
    process_failed_tasks_notification
)
from app.tasks.monitoring_tasks import (
    update_queue_length_metrics,
    perform_system_health_check
)
from app.tasks.maintenance_tasks import cleanup_stale_task_statuses
from app.tasks.scheduled_tasks import beat_schedule

# 导出celery应用实例
__all__ = [
    # Celery实例
    'celery_app',
    
    # 作文批改任务
    'process_essay_correction',
    'batch_process_essays',
    'high_priority_essay_correction',
    
    # 用户相关任务
    'send_notification_email',
    'send_verification_code',
    'process_user_activity',
    'cleanup_inactive_users',
    
    # 订阅相关任务
    'process_subscription_task',
    'renew_expiring_subscriptions',
    
    # 备份相关任务
    'backup_database',
    'restore_database',
    'list_backups',
    
    # 分析报表任务
    'generate_daily_stats',
    'generate_monthly_report',
    'generate_user_progress_report',
    
    # 通知相关任务
    'send_task_failure_notification',
    'process_failed_tasks_notification',
    
    # 监控相关任务
    'update_queue_length_metrics',
    'perform_system_health_check',
    
    # 维护相关任务
    'cleanup_stale_task_statuses',
    
    # Celery Beat配置
    'beat_schedule'
] 