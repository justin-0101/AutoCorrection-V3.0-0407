#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务包初始化模块
导入和注册任务相关模块
"""

import logging

# 初始化日志
logger = logging.getLogger(__name__)

# 导入celery应用实例
from app.tasks.celery_app import celery_app

# 导入信号处理器并注册
try:
    from app.tasks.signal_handlers import register_signal_handlers
    register_signal_handlers()
    logger.info("任务状态跟踪信号处理器已初始化")
except Exception as e:
    logger.warning(f"初始化任务状态跟踪信号处理器时发生错误: {str(e)}")

# 使用函数延迟导入任务，避免循环导入问题
def load_tasks():
    """加载所有任务模块"""
    global process_essay_correction, batch_process_essays, high_priority_essay_correction
    global send_notification_email, send_verification_code, process_user_activity, cleanup_inactive_users
    global process_subscription_task, renew_expiring_subscriptions
    global backup_database, restore_database, list_backups
    global generate_daily_stats, generate_monthly_report, generate_user_progress_report
    global send_task_failure_notification, process_failed_tasks_notification
    global update_queue_length_metrics, perform_system_health_check
    global cleanup_stale_task_statuses, beat_schedule
    
    try:
        # 导入任务模块，使celery能够发现这些任务
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
        
        logger.info("所有任务模块已成功加载")
        return True
    except Exception as e:
        logger.error(f"加载任务模块时出错: {str(e)}")
        return False

# 延迟导出celery应用实例和任务
__all__ = [
    # Celery实例
    'celery_app',
    
    # 任务加载函数
    'load_tasks'
]

# 立即加载任务，使celery可以识别这些任务
load_tasks() 