#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员使用统计模块
负责收集、分析和展示会员使用情况的详细统计
"""

import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import calendar

from sqlalchemy import func, and_, or_, desc, case
from sqlalchemy.sql import extract

from app.models.db import db
from app.models.user import User
from app.models.essay import Essay
from app.models.usage_log import UsageLog
from app.models.membership import Membership, MembershipPlan
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)

class UsageAnalytics:
    """会员使用统计服务类"""
    
    @staticmethod
    def log_usage_event(user_id: int, event_type: str, resource_id: Optional[int] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        记录用户使用事件
        
        Args:
            user_id: 用户ID
            event_type: 事件类型，如'essay_submit', 'essay_view', 'download_report'
            resource_id: 相关资源ID（可选）
            metadata: 事件元数据（可选）
            
        Returns:
            Dict: 记录结果
        """
        try:
            # 获取用户会员信息
            membership = Membership.query.filter_by(user_id=user_id).first()
            if not membership:
                return {
                    "status": "error",
                    "message": "未找到会员信息"
                }
            
            # 创建使用记录
            usage_log = UsageLog(
                user_id=user_id,
                membership_id=membership.id,
                event_type=event_type,
                resource_id=resource_id,
                metadata=metadata or {},
                created_at=datetime.datetime.utcnow().timestamp()
            )
            
            # 保存到数据库
            db.session.add(usage_log)
            db.session.commit()
            
            # 如果是作文提交事件，增加会员使用计数
            if event_type == 'essay_submit':
                membership.increment_usage()
            
            logger.info(f"用户 {user_id} 使用事件 {event_type} 已记录")
            
            return {
                "status": "success",
                "message": "使用事件已记录",
                "usage_log_id": usage_log.id
            }
            
        except Exception as e:
            logger.error(f"记录使用事件时出错: {str(e)}", exc_info=True)
            db.session.rollback()
            return {
                "status": "error",
                "message": f"记录使用事件失败: {str(e)}"
            }
    
    @staticmethod
    def get_user_usage_history(user_id: int, event_type: Optional[str] = None,
                              start_date: Optional[datetime.datetime] = None,
                              end_date: Optional[datetime.datetime] = None,
                              limit: int = 100) -> Dict[str, Any]:
        """
        获取用户使用历史记录
        
        Args:
            user_id: 用户ID
            event_type: 筛选特定事件类型（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 返回记录数量限制
            
        Returns:
            Dict: 使用历史记录
        """
        try:
            # 构建查询
            query = UsageLog.query.filter_by(user_id=user_id)
            
            # 应用筛选条件
            if event_type:
                query = query.filter_by(event_type=event_type)
            
            if start_date:
                query = query.filter(UsageLog.created_at >= start_date.timestamp())
            
            if end_date:
                query = query.filter(UsageLog.created_at <= end_date.timestamp())
            
            # 获取记录
            logs = query.order_by(desc(UsageLog.created_at)).limit(limit).all()
            
            # 格式化记录
            usage_logs = []
            for log in logs:
                usage_logs.append({
                    "id": log.id,
                    "event_type": log.event_type,
                    "resource_id": log.resource_id,
                    "metadata": log.metadata,
                    "created_at": datetime.datetime.fromtimestamp(log.created_at).isoformat()
                })
            
            return {
                "status": "success",
                "user_id": user_id,
                "total_records": len(usage_logs),
                "usage_logs": usage_logs
            }
            
        except Exception as e:
            logger.error(f"获取用户使用历史记录时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取用户使用历史记录失败: {str(e)}"
            }
    
    @staticmethod
    def get_feature_usage_stats(feature: str, period_days: int = 30) -> Dict[str, Any]:
        """
        获取特定功能的使用统计
        
        Args:
            feature: 功能名称
            period_days: 统计周期天数
            
        Returns:
            Dict: 功能使用统计
        """
        try:
            # 计算统计起始时间
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=period_days)
            start_timestamp = start_date.timestamp()
            
            # 获取使用该功能的事件记录
            feature_events = UsageLog.query.filter(
                UsageLog.event_type == feature,
                UsageLog.created_at >= start_timestamp
            ).all()
            
            # 按会员等级分组统计
            plan_usage = defaultdict(int)
            user_ids = set()
            
            for event in feature_events:
                user_ids.add(event.user_id)
                
                # 获取用户会员信息
                membership = Membership.query.filter_by(
                    user_id=event.user_id, 
                    created_at__lte=event.created_at
                ).order_by(desc(Membership.created_at)).first()
                
                if membership:
                    plan = MembershipPlan.query.get(membership.plan_id)
                    if plan:
                        plan_usage[plan.code] += 1
            
            # 按日期分组统计
            daily_usage = defaultdict(int)
            for event in feature_events:
                date_str = datetime.datetime.fromtimestamp(event.created_at).strftime('%Y-%m-%d')
                daily_usage[date_str] += 1
            
            # 整理时间序列数据
            time_series = []
            current_date = start_date.date()
            end_date = datetime.datetime.utcnow().date()
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                time_series.append({
                    "date": date_str,
                    "count": daily_usage.get(date_str, 0)
                })
                current_date += datetime.timedelta(days=1)
            
            return {
                "status": "success",
                "feature": feature,
                "period_days": period_days,
                "total_usage": len(feature_events),
                "unique_users": len(user_ids),
                "usage_by_plan": dict(plan_usage),
                "time_series": time_series,
                "average_daily_usage": round(len(feature_events) / period_days, 2)
            }
            
        except Exception as e:
            logger.error(f"获取功能使用统计时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取功能使用统计失败: {str(e)}"
            }
    
    @staticmethod
    def get_membership_usage_trends(period_days: int = 90) -> Dict[str, Any]:
        """
        获取会员使用趋势统计
        
        Args:
            period_days: 统计周期天数
            
        Returns:
            Dict: 会员使用趋势统计
        """
        try:
            # 计算统计起始时间
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=period_days)
            start_timestamp = start_date.timestamp()
            
            # 获取该时间段内的使用记录
            usage_logs = UsageLog.query.filter(
                UsageLog.created_at >= start_timestamp
            ).all()
            
            # 按照会员计划和日期分组统计
            plan_daily_usage = defaultdict(lambda: defaultdict(int))
            event_type_counts = defaultdict(int)
            
            for log in usage_logs:
                date_str = datetime.datetime.fromtimestamp(log.created_at).strftime('%Y-%m-%d')
                
                # 获取用户会员信息
                membership = Membership.query.filter_by(user_id=log.user_id).first()
                if membership:
                    plan = MembershipPlan.query.get(membership.plan_id)
                    if plan:
                        plan_daily_usage[plan.code][date_str] += 1
                
                # 统计事件类型
                event_type_counts[log.event_type] += 1
            
            # 整理时间序列数据
            time_series = []
            current_date = start_date.date()
            end_date = datetime.datetime.utcnow().date()
            
            all_plans = MembershipPlan.query.all()
            plan_codes = [plan.code for plan in all_plans]
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                
                # 创建日期条目
                date_entry = {
                    "date": date_str,
                    "plans": {}
                }
                
                # 添加各会员计划的使用量
                for plan_code in plan_codes:
                    date_entry["plans"][plan_code] = plan_daily_usage[plan_code].get(date_str, 0)
                
                time_series.append(date_entry)
                current_date += datetime.timedelta(days=1)
            
            # 计算使用高峰
            peak_usage_day = max(time_series, key=lambda x: sum(x["plans"].values()))
            peak_day = peak_usage_day["date"]
            peak_count = sum(peak_usage_day["plans"].values())
            
            # 计算平均每日使用量
            avg_daily_usage = round(len(usage_logs) / period_days, 2)
            
            # 计算每个计划的使用量百分比
            plan_totals = {plan_code: sum(daily_usage.values()) for plan_code, daily_usage in plan_daily_usage.items()}
            total_usage = sum(plan_totals.values())
            
            plan_percentages = {}
            for plan_code, usage_count in plan_totals.items():
                plan_percentages[plan_code] = round(usage_count / total_usage * 100, 2) if total_usage > 0 else 0
            
            return {
                "status": "success",
                "period_days": period_days,
                "total_usage": len(usage_logs),
                "event_type_counts": dict(event_type_counts),
                "plan_usage_totals": plan_totals,
                "plan_usage_percentages": plan_percentages,
                "average_daily_usage": avg_daily_usage,
                "peak_usage": {
                    "date": peak_day,
                    "count": peak_count
                },
                "time_series": time_series
            }
            
        except Exception as e:
            logger.error(f"获取会员使用趋势统计时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取会员使用趋势统计失败: {str(e)}"
            }
    
    @staticmethod
    def get_user_engagement_metrics(user_id: int) -> Dict[str, Any]:
        """
        获取用户参与度指标
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户参与度指标数据
        """
        try:
            # 获取用户信息
            user = User.query.get(user_id)
            if not user:
                return {
                    "status": "error",
                    "message": "用户不存在"
                }
            
            # 获取用户会员信息
            membership = Membership.query.filter_by(user_id=user_id).first()
            if not membership:
                return {
                    "status": "error",
                    "message": "未找到会员信息"
                }
            
            # 计算使用频率 - 过去30天的平均每日使用次数
            thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
            
            # 按日期统计使用次数
            daily_usage = db.session.query(
                func.date(func.datetime(UsageLog.created_at, 'unixepoch')).label('date'),
                func.count(UsageLog.id).label('count')
            ).filter(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= thirty_days_ago.timestamp()
            ).group_by('date').all()
            
            # 计算活跃天数和使用频率
            active_days = len(daily_usage)
            total_usage = sum(count for _, count in daily_usage)
            usage_frequency = round(total_usage / 30, 2)  # 平均每日使用次数
            
            # 计算连续活跃天数
            current_streak = 0
            max_streak = 0
            
            # 将日期转换为集合以便快速查找
            active_dates = {date_str for date_str, _ in daily_usage}
            
            # 计算当前连续活跃天数
            today = datetime.datetime.utcnow().date()
            current_date = today
            
            while current_date.strftime('%Y-%m-%d') in active_dates:
                current_streak += 1
                current_date -= datetime.timedelta(days=1)
            
            # 计算历史最大连续活跃天数
            # 这里简化处理，实际上需要遍历所有历史数据
            all_logs = UsageLog.query.filter_by(user_id=user_id).order_by(UsageLog.created_at).all()
            if all_logs:
                active_days_set = set()
                for log in all_logs:
                    date_str = datetime.datetime.fromtimestamp(log.created_at).strftime('%Y-%m-%d')
                    active_days_set.add(date_str)
                
                # 将日期转换为datetime对象并排序
                active_days_sorted = sorted([datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in active_days_set])
                
                # 计算最大连续天数
                if active_days_sorted:
                    current_count = 1
                    for i in range(1, len(active_days_sorted)):
                        if (active_days_sorted[i] - active_days_sorted[i-1]).days == 1:
                            current_count += 1
                        else:
                            max_streak = max(max_streak, current_count)
                            current_count = 1
                    
                    max_streak = max(max_streak, current_count)
            
            # 计算留存率 - 是否持续使用本月和上月都有登录
            this_month_start = datetime.datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 计算上个月的开始和结束
            if this_month_start.month == 1:
                last_month_start = this_month_start.replace(year=this_month_start.year-1, month=12)
            else:
                last_month_start = this_month_start.replace(month=this_month_start.month-1)
            
            # 检查本月和上月是否都有活动
            this_month_active = UsageLog.query.filter(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= this_month_start.timestamp()
            ).first() is not None
            
            last_month_active = UsageLog.query.filter(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= last_month_start.timestamp(),
                UsageLog.created_at < this_month_start.timestamp()
            ).first() is not None
            
            retained = this_month_active and last_month_active
            
            # 获取用户最常使用的功能
            top_features = db.session.query(
                UsageLog.event_type,
                func.count(UsageLog.id).label('count')
            ).filter(
                UsageLog.user_id == user_id
            ).group_by(UsageLog.event_type).order_by(desc('count')).limit(5).all()
            
            top_features_list = [{"feature": feature, "count": count} for feature, count in top_features]
            
            return {
                "status": "success",
                "user_id": user_id,
                "username": user.username,
                "membership_level": membership.plan.name if membership.plan else "未知",
                "active_days_last_30": active_days,
                "active_percentage_last_30": round(active_days / 30 * 100, 2),
                "usage_frequency": usage_frequency,
                "current_streak": current_streak,
                "max_streak": max_streak,
                "retained": retained,
                "top_features_used": top_features_list,
                "engagement_score": round((active_days / 30 * 0.4 + min(usage_frequency / 5, 1) * 0.3 + 
                                          min(current_streak / 7, 1) * 0.2 + (1 if retained else 0) * 0.1) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"获取用户参与度指标时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取用户参与度指标失败: {str(e)}"
            }
    
    @staticmethod
    def get_usage_quota_alerts() -> Dict[str, Any]:
        """
        获取即将达到使用配额的用户列表
        
        Returns:
            Dict: 需要发送警报的用户列表
        """
        try:
            # 查找使用量已达到配额80%的用户
            users_at_limit = []
            
            # 查询所有活跃会员
            active_memberships = Membership.query.filter_by(is_active=True).all()
            
            for membership in active_memberships:
                # 获取会员计划
                plan = MembershipPlan.query.get(membership.plan_id)
                if not plan:
                    continue
                
                # 检查每日使用量
                daily_limit = plan.max_essays_per_day
                if daily_limit > 0:
                    daily_usage_percentage = (membership.essays_used_today / daily_limit) * 100
                    if daily_usage_percentage >= 80:
                        user = User.query.get(membership.user_id)
                        if user:
                            users_at_limit.append({
                                "user_id": user.id,
                                "username": user.username,
                                "email": user.email,
                                "quota_type": "daily",
                                "limit": daily_limit,
                                "used": membership.essays_used_today,
                                "percentage": round(daily_usage_percentage, 2)
                            })
                
                # 检查总使用量
                total_limit = plan.max_essays_total
                if total_limit > 0:
                    total_usage_percentage = (membership.essays_used_total / total_limit) * 100
                    if total_usage_percentage >= 80:
                        user = User.query.get(membership.user_id)
                        if user and not any(alert["user_id"] == user.id and alert["quota_type"] == "total" for alert in users_at_limit):
                            users_at_limit.append({
                                "user_id": user.id,
                                "username": user.username,
                                "email": user.email,
                                "quota_type": "total",
                                "limit": total_limit,
                                "used": membership.essays_used_total,
                                "percentage": round(total_usage_percentage, 2)
                            })
            
            return {
                "status": "success",
                "alerts_count": len(users_at_limit),
                "users_at_limit": users_at_limit
            }
            
        except Exception as e:
            logger.error(f"获取使用配额警报时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取使用配额警报失败: {str(e)}"
            } 