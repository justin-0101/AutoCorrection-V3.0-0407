#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据分析异步任务模块
处理数据统计、报表生成相关的异步任务
"""

import logging
import time
import datetime
import json
import os
from pathlib import Path
from celery import shared_task

from app.models.db import db
from app.models.user import User
from app.models.essay import Essay
from app.models.user_activity import UserActivity
from app.core.notification.notification_service import NotificationService
from app.config import config
from app.tasks.batch_optimization import (
    batch_processor, 
    iterate_in_chunks, 
    monitor_performance,
    prioritize_task
)
from app.tasks.celery_app import celery_app

# 获取logger
logger = logging.getLogger(__name__)

# 创建通知服务实例
notification_service = NotificationService()

# 报表存储目录
REPORTS_DIR = config.BACKUP_CONFIG.get('reports_dir', 'reports')

# 优先级计算函数
def calculate_report_priority(date_str=None, **kwargs):
    """
    计算报表生成任务的优先级
    
    Args:
        date_str: 日期字符串
        
    Returns:
        int: 优先级(1-10)
    """
    # 如果是当天的报表，设置较低优先级
    if date_str:
        try:
            report_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.datetime.now()
            
            # 如果是今天的报表，优先级较低
            if report_date.date() == today.date():
                return 3
            
            # 如果是昨天的报表，优先级中等
            if (today.date() - report_date.date()).days == 1:
                return 5
                
            # 如果是更早的报表，优先级较高
            return 7
        except Exception:
            pass
    
    # 默认中等优先级
    return 5


@celery_app.task(
    name='app.tasks.analytics_tasks.generate_daily_stats',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
@prioritize_task(calculate_report_priority)
@monitor_performance(name="daily_stats_generation")
def generate_daily_stats(self, date_str=None):
    """
    生成每日统计数据
    
    Args:
        self: Celery任务实例
        date_str: 日期字符串，格式为 YYYY-MM-DD，默认为昨天
    
    Returns:
        dict: 统计结果
    """
    try:
        # 确定统计日期
        if date_str:
            try:
                target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                logger.error(f"日期格式无效: {date_str}，应为 YYYY-MM-DD")
                return {
                    "status": "error",
                    "message": f"日期格式无效: {date_str}，应为 YYYY-MM-DD"
                }
        else:
            # 默认使用昨天
            target_date = datetime.datetime.now() - datetime.timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        logger.info(f"开始生成日报表，日期: {date_str}")
        
        # 计算时间范围
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 转换为时间戳
        start_timestamp = start_time.timestamp()
        end_timestamp = end_time.timestamp()
        
        with db.session() as session:
            # 获取当日新用户数量
            new_users_count = session.query(User).filter(
                User.created_at.between(start_timestamp, end_timestamp)
            ).count()
            
            # 获取当日活跃用户数
            active_users_count = session.query(User.id).distinct().join(
                UserActivity,
                User.id == UserActivity.user_id
            ).filter(
                UserActivity.created_at.between(start_timestamp, end_timestamp)
            ).count()
            
            # 获取当日作文提交数
            essays_count = session.query(Essay).filter(
                Essay.created_at.between(start_timestamp, end_timestamp)
            ).count()
            
            # 获取当日平均作文分数
            avg_score_result = session.query(db.func.avg(Essay.score)).filter(
                Essay.created_at.between(start_timestamp, end_timestamp),
                Essay.status == 'completed'
            ).scalar()
            avg_score = round(float(avg_score_result or 0), 2)
            
            # 各分数段分布
            score_distribution = {}
            for score_range in [(0, 60), (60, 70), (70, 80), (80, 90), (90, 100)]:
                lower, upper = score_range
                count = session.query(Essay).filter(
                    Essay.created_at.between(start_timestamp, end_timestamp),
                    Essay.status == 'completed',
                    Essay.score >= lower,
                    Essay.score < upper if upper < 100 else Essay.score <= upper
                ).count()
                score_distribution[f"{lower}-{upper}"] = count
            
            # 用户活动类型统计
            activity_types = session.query(
                UserActivity.activity_type,
                db.func.count(UserActivity.id)
            ).filter(
                UserActivity.created_at.between(start_timestamp, end_timestamp)
            ).group_by(UserActivity.activity_type).all()
            
            activity_stats = {activity_type: count for activity_type, count in activity_types}
            
            # 组装统计数据
            stats = {
                "date": date_str,
                "new_users": new_users_count,
                "active_users": active_users_count,
                "essays_submitted": essays_count,
                "average_score": avg_score,
                "score_distribution": score_distribution,
                "activity_stats": activity_stats,
                "generated_at": datetime.datetime.now().isoformat()
            }
            
            # 确保报表目录存在
            reports_dir = Path(REPORTS_DIR) / 'daily'
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存统计数据到文件
            report_file = reports_dir / f"daily_stats_{date_str}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"日报表生成完成，已保存至: {report_file}")
            
            return {
                "status": "success",
                "message": f"日报表生成完成",
                "report_file": str(report_file),
                "stats": stats
            }
    
    except Exception as e:
        logger.error(f"生成日报表异常: {str(e)}", exc_info=True)
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 {self.default_retry_delay} 秒后重试生成日报表")
            self.retry(exc=e, countdown=self.default_retry_delay)
        
        return {
            "status": "error",
            "message": f"生成日报表异常: {str(e)}"
        }


@celery_app.task(
    name='app.tasks.analytics_tasks.generate_monthly_report',
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    soft_time_limit=1800,  # 30分钟超时
    time_limit=2100,       # 35分钟硬超时
)
@monitor_performance(name="monthly_report_generation")
def generate_monthly_report(self, year_month=None, send_to_admin=True):
    """
    生成月度报表，使用批处理优化处理大量数据
    
    Args:
        self: Celery任务实例
        year_month: 年月字符串，格式为YYYY-MM，默认为上个月
        send_to_admin: 是否发送报表给管理员
    
    Returns:
        dict: 报表生成结果
    """
    overall_start_time = time.time()
    try:
        # 确定统计月份
        if year_month:
            try:
                target_month = datetime.datetime.strptime(year_month, '%Y-%m')
            except ValueError:
                logger.error(f"月份格式无效: {year_month}，应为 YYYY-MM")
                return {
                    "status": "error",
                    "message": f"月份格式无效: {year_month}，应为 YYYY-MM"
                }
        else:
            # 默认使用上个月
            today = datetime.datetime.now()
            if today.month == 1:
                target_month = datetime.datetime(today.year - 1, 12, 1)
            else:
                target_month = datetime.datetime(today.year, today.month - 1, 1)
        
        year_month_str = target_month.strftime('%Y-%m')
        logger.info(f"开始生成月度报表，月份: {year_month_str}")
        
        # 计算月份的开始和结束时间
        month_start = target_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 计算月末
        if target_month.month == 12:
            next_month = datetime.datetime(target_month.year + 1, 1, 1)
        else:
            next_month = datetime.datetime(target_month.year, target_month.month + 1, 1)
        
        month_end = next_month - datetime.timedelta(microseconds=1)
        
        # 转换为时间戳
        start_timestamp = month_start.timestamp()
        end_timestamp = month_end.timestamp()
        
        # 使用优化的数据处理
        with db.session() as session:
            logger.info(f"开始查询用户统计数据")
            query_start_time = time.time()
            
            # 获取本月用户增长情况
            new_users_count = session.query(User).filter(
                User.created_at.between(start_timestamp, end_timestamp)
            ).count()
            
            total_users_count = session.query(User).filter(
                User.created_at <= end_timestamp
            ).count()
            
            # 获取本月活跃用户数和活跃率 - 使用优化的分块查询
            logger.info(f"开始分块查询活跃用户")
            active_users_set = set()
            
            # 优化查询，避免一次性获取所有记录
            user_activity_query = session.query(UserActivity.user_id).distinct().filter(
                UserActivity.created_at.between(start_timestamp, end_timestamp)
            )
            
            # 使用迭代器分块获取数据
            for chunk in iterate_in_chunks(user_activity_query, chunk_size=5000):
                # 将当前块的用户ID添加到集合中
                for activity in chunk:
                    active_users_set.add(activity.user_id)
            
            active_users_count = len(active_users_set)
            query_time = time.time() - query_start_time
            logger.info(f"用户统计查询完成，耗时: {query_time:.2f}秒")
            
            active_rate = round(active_users_count / total_users_count * 100, 2) if total_users_count > 0 else 0
            
            # 获取本月作文提交数 - 使用分块处理
            logger.info(f"开始计算作文统计数据")
            essays_count = session.query(Essay).filter(
                Essay.created_at.between(start_timestamp, end_timestamp)
            ).count()
            
            # 获取本月平均作文分数 - 使用分块处理以减轻内存压力
            avg_score_processing_start = time.time()
            
            essays_query = session.query(Essay.score).filter(
                Essay.created_at.between(start_timestamp, end_timestamp),
                Essay.status == 'completed'
            )
            
            # 分块计算平均分
            total_score = 0.0
            total_count = 0
            
            for chunk in iterate_in_chunks(essays_query, chunk_size=5000):
                for essay in chunk:
                    if essay.score is not None:
                        total_score += essay.score
                        total_count += 1
            
            avg_score = round(total_score / total_count, 2) if total_count > 0 else 0.0
            logger.info(f"平均分计算完成，平均分: {avg_score}, 耗时: {time.time() - avg_score_processing_start:.2f}秒")
            
            # 各分数段分布 - 使用批处理优化
            score_distribution = {
                "0-60": 0, "60-70": 0, "70-80": 0, "80-90": 0, "90-100": 0
            }
            
            def get_score_range(score):
                if score < 60:
                    return "0-60"
                elif score < 70:
                    return "60-70"
                elif score < 80:
                    return "70-80"
                elif score < 90:
                    return "80-90"
                else:
                    return "90-100"
            
            # 分块处理分数分布
            scores_query = session.query(Essay.score).filter(
                Essay.created_at.between(start_timestamp, end_timestamp),
                Essay.status == 'completed'
            )
            
            for chunk in iterate_in_chunks(scores_query, chunk_size=5000):
                for essay in chunk:
                    if essay.score is not None:
                        score_range = get_score_range(essay.score)
                        score_distribution[score_range] += 1
            
            # 用户活动类型统计
            activity_types = session.query(
                UserActivity.activity_type,
                db.func.count(UserActivity.id)
            ).filter(
                UserActivity.created_at.between(start_timestamp, end_timestamp)
            ).group_by(UserActivity.activity_type).all()
            
            activity_stats = {activity_type: count for activity_type, count in activity_types}
            
            # 获取每日作文趋势数据
            logger.info(f"计算每日作文趋势")
            daily_trends_start = time.time()
            
            # 使用高效的SQL聚合查询
            daily_counts = session.query(
                db.func.strftime('%Y-%m-%d', db.func.datetime(Essay.created_at, 'unixepoch')).label('date'),
                db.func.count(Essay.id).label('count')
            ).filter(
                Essay.created_at.between(start_timestamp, end_timestamp)
            ).group_by('date').all()
            
            # 创建所有日期的映射，包括没有作文的日期
            all_days = {}
            current_date = month_start
            while current_date <= month_end:
                day_str = current_date.strftime('%Y-%m-%d')
                all_days[day_str] = 0
                current_date += datetime.timedelta(days=1)
            
            # 填充实际数据
            for date_str, count in daily_counts:
                if date_str in all_days:
                    all_days[date_str] = count
            
            # 转换为所需的格式
            daily_essay_trends = [{"date": date, "count": count} for date, count in all_days.items()]
            
            logger.info(f"每日趋势计算完成，耗时: {time.time() - daily_trends_start:.2f}秒")
            
            # 组装报表数据
            report_data = {
                "year_month": year_month_str,
                "period": {
                    "start": month_start.strftime('%Y-%m-%d'),
                    "end": month_end.strftime('%Y-%m-%d')
                },
                "user_stats": {
                    "new_users": new_users_count,
                    "total_users": total_users_count,
                    "active_users": active_users_count,
                    "active_rate": f"{active_rate}%"
                },
                "essay_stats": {
                    "total_submitted": essays_count,
                    "average_score": avg_score,
                    "daily_trends": daily_essay_trends,
                    "score_distribution": score_distribution
                },
                "activity_stats": activity_stats,
                "generated_at": datetime.datetime.now().isoformat()
            }
            
            # 确保报表目录存在
            reports_dir = Path(REPORTS_DIR) / 'monthly'
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存报表数据到文件
            report_file = reports_dir / f"monthly_report_{year_month_str}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"月度报表生成完成，已保存至: {report_file}, 总耗时: {time.time() - overall_start_time:.2f}秒")
            
            # 如果需要，发送报表给管理员
            if send_to_admin:
                # 生成简单的文本报表
                report_summary = f"""
作文批改系统 - {year_month_str} 月度报表

统计周期: {month_start.strftime('%Y-%m-%d')} 至 {month_end.strftime('%Y-%m-%d')}

用户统计:
- 新增用户: {new_users_count}
- 总用户数: {total_users_count}
- 活跃用户: {active_users_count}
- 活跃率: {active_rate}%

作文统计:
- 提交作文数: {essays_count}
- 平均分数: {avg_score}

分数分布:
- 0-60分: {score_distribution.get("0-60", 0)}
- 60-70分: {score_distribution.get("60-70", 0)}
- 70-80分: {score_distribution.get("70-80", 0)}
- 80-90分: {score_distribution.get("80-90", 0)}
- 90-100分: {score_distribution.get("90-100", 0)}

完整报表已附件形式提供。
"""
                
                # 从配置中获取管理员邮箱
                admin_emails = config.ADMIN_CONFIG.get('admin_emails', [])
                
                if admin_emails:
                    try:
                        # 使用通知服务发送邮件
                        for admin_email in admin_emails:
                            notification_service.send_admin_report_notification(
                                email=admin_email,
                                subject=f"作文批改系统 - {year_month_str} 月度报表",
                                content=report_summary,
                                attachments=[str(report_file)]
                            )
                        logger.info(f"月度报表已发送至管理员: {', '.join(admin_emails)}")
                    except Exception as e:
                        logger.error(f"发送月度报表邮件异常: {str(e)}")
            
            return {
                "status": "success",
                "message": "月度报表生成完成",
                "report_file": str(report_file),
                "report_data": report_data,
                "processing_time": time.time() - overall_start_time
            }
    
    except Exception as e:
        logger.error(f"生成月度报表异常: {str(e)}", exc_info=True)
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            logger.info(f"将在 {self.default_retry_delay} 秒后重试生成月度报表")
            self.retry(exc=e, countdown=self.default_retry_delay)
        
        return {
            "status": "error",
            "message": f"生成月度报表异常: {str(e)}",
            "processing_time": time.time() - overall_start_time
        }


@celery_app.task(
    name='app.tasks.analytics_tasks.generate_user_progress_report',
    bind=True,
    max_retries=2
)
@prioritize_task(calculate_report_priority)
def generate_user_progress_report(self, user_id, period=30):
    """
    生成用户进度报表
    分析用户一段时间内的作文提交情况和成绩变化
    
    Args:
        self: Celery任务实例
        user_id: 用户ID
        period: 统计周期(天数)，默认30天
    
    Returns:
        dict: 用户进度报表
    """
    try:
        logger.info(f"开始生成用户进度报表，用户ID: {user_id}, 周期: {period}天")
        
        # 计算时间范围
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=period)
        
        # 转换为时间戳
        start_timestamp = start_date.timestamp()
        end_timestamp = end_date.timestamp()
        
        with db.session() as session:
            # 获取用户信息
            user = session.query(User).get(user_id)
            if not user:
                logger.error(f"用户不存在，ID: {user_id}")
                return {
                    "status": "error",
                    "message": f"用户不存在，ID: {user_id}"
                }
            
            # 获取用户在此期间的作文
            essays = session.query(Essay).filter(
                Essay.user_id == user_id,
                Essay.created_at.between(start_timestamp, end_timestamp),
                Essay.status == 'completed'
            ).order_by(Essay.created_at).all()
            
            if not essays:
                logger.info(f"用户在此期间没有完成的作文，用户ID: {user_id}")
                return {
                    "status": "success",
                    "message": "用户在此期间没有完成的作文",
                    "user_id": user_id,
                    "period": period,
                    "essays_count": 0,
                    "progress": None
                }
            
            # 分析作文数据
            essay_details = []
            scores = []
            
            for essay in essays:
                essay_details.append({
                    "id": essay.id,
                    "title": essay.title,
                    "submission_date": datetime.datetime.fromtimestamp(essay.created_at).strftime('%Y-%m-%d'),
                    "score": essay.score,
                    "word_count": essay.word_count
                })
                scores.append(essay.score)
            
            # 计算进步情况
            progress_data = {
                "average_score": round(sum(scores) / len(scores), 2),
                "lowest_score": min(scores),
                "highest_score": max(scores),
                "earliest_score": scores[0] if scores else None,
                "latest_score": scores[-1] if scores else None,
                "score_change": round(scores[-1] - scores[0], 2) if len(scores) > 1 else 0,
                "essays_count": len(essays),
                "submission_frequency": round(len(essays) / period, 2),  # 每天平均提交数
                "detail": essay_details
            }
            
            # 进步分析
            progress_analysis = ""
            if len(scores) > 1:
                if scores[-1] > scores[0]:
                    progress_analysis = f"在过去{period}天内，您的作文成绩提高了{progress_data['score_change']}分，继续保持！"
                elif scores[-1] < scores[0]:
                    progress_analysis = f"在过去{period}天内，您的作文成绩下降了{abs(progress_data['score_change'])}分，建议加强练习。"
                else:
                    progress_analysis = f"在过去{period}天内，您的作文成绩保持稳定。"
            else:
                progress_analysis = "数据样本太少，无法进行准确分析。建议多提交作文以获得更准确的进步分析。"
            
            progress_data["analysis"] = progress_analysis
            
            # 生成报表
            report = {
                "user_id": user_id,
                "username": user.username,
                "period": {
                    "days": period,
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d')
                },
                "progress": progress_data,
                "generated_at": datetime.datetime.now().isoformat()
            }
            
            # 确保报表目录存在
            reports_dir = Path(REPORTS_DIR) / 'users'
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存报表到文件
            report_file = reports_dir / f"progress_report_user_{user_id}_{end_date.strftime('%Y%m%d')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"用户进度报表生成完成，用户ID: {user_id}")
            
            return {
                "status": "success",
                "message": "用户进度报表生成完成",
                "report_file": str(report_file),
                "report": report
            }
    
    except Exception as e:
        logger.error(f"生成用户进度报表异常，用户ID: {user_id}: {str(e)}", exc_info=True)
        
        # 尝试重试
        if self.request.retries < self.max_retries:
            self.retry(exc=e, countdown=60)
        
        return {
            "status": "error",
            "message": f"生成用户进度报表异常: {str(e)}"
        } 