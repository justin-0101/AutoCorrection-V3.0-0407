#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异步任务包
包含所有Celery异步任务的定义和配置
"""

from app.tasks.correction_tasks import (
    process_essay_correction,
    batch_process_essays
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
from app.tasks.scheduled_tasks import beat_schedule

__all__ = [
    # 作文批改任务
    'process_essay_correction',
    'batch_process_essays',
    
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
    
    # Celery Beat配置
    'beat_schedule'
] 