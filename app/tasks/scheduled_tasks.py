#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
定时任务配置模块
配置 Celery Beat 的定时任务调度
"""

from celery.schedules import crontab

# Celery Beat 调度配置
beat_schedule = {
    # 每天凌晨2点生成前一天的统计数据
    'generate-daily-stats': {
        'task': 'app.tasks.analytics_tasks.generate_daily_stats',
        'schedule': crontab(hour=2, minute=0)
    },
    
    # 每月1号凌晨3点生成上月的月度报表
    'generate-monthly-report': {
        'task': 'app.tasks.analytics_tasks.generate_monthly_report',
        'schedule': crontab(0, 3, day_of_month=1)
    },
    
    # 每天检查即将过期的会员订阅（提前3天提醒）
    'check-expiring-subscriptions': {
        'task': 'subscription.check_expiring_subscriptions',
        'schedule': crontab(hour=10, minute=0)  # 每天上午10点执行
    },
    
    # 每天处理已过期的会员订阅
    'process-expired-subscriptions': {
        'task': 'subscription.process_expired_subscriptions',
        'schedule': crontab(hour=1, minute=0)  # 每天凌晨1点执行
    },
    
    # 每4小时处理一次自动续费支付失败的重试
    'process-payment-retry': {
        'task': 'subscription.process_payment_retry',
        'schedule': crontab(minute=0, hour='*/4')
    },
    
    # 每周生成一次会员订阅报表
    'generate-subscription-report': {
        'task': 'subscription.generate_subscription_report',
        'schedule': crontab(hour=4, minute=0, day_of_week=1)  # 每周一凌晨4点
    },
    
    # 每天优化一次会员续费方案
    'optimize-renewal-offers': {
        'task': 'subscription.optimize_renewal_offers',
        'schedule': crontab(hour=5, minute=0)  # 每天凌晨5点
    },
    
    # 每周分析一次会员流失情况
    'analyze-subscription-churn': {
        'task': 'subscription.analyze_subscription_churn',
        'schedule': crontab(hour=3, minute=0, day_of_week=1)  # 每周一凌晨3点
    },
    
    # 每天发送续订提醒
    'send-subscription-renewal-reminders': {
        'task': 'tasks.send_subscription_renewal_reminders',
        'schedule': crontab(hour=11, minute=0),  # 每天上午11点
        'args': (7,)  # 提前7天提醒
    },
    
    # 每天备份数据库
    'backup-database': {
        'task': 'app.tasks.backup_tasks.backup_database',
        'schedule': crontab(hour=0, minute=0)  # 每天凌晨12点
    }
} 