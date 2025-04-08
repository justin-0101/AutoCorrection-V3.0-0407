#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员数据分析模块
处理会员使用统计、转化率分析、续费率分析等数据分析功能
"""

import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple
from calendar import monthrange
from collections import defaultdict

from sqlalchemy import func, and_, or_, desc, text
from sqlalchemy.sql import extract

from app.models.db import db
from app.models.user import User
from app.models.membership import Membership, MembershipPlan
from app.models.subscription import Subscription
from app.models.essay import Essay

logger = logging.getLogger(__name__)

class MembershipAnalytics:
    """会员数据分析服务类"""
    
    @staticmethod
    def get_membership_usage_stats(user_id: int) -> Dict[str, Any]:
        """
        获取特定用户的会员使用统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 会员使用统计数据
        """
        try:
            # 查询用户会员信息
            membership = Membership.query.filter_by(user_id=user_id).first()
            if not membership:
                return {
                    "status": "error",
                    "message": "未找到会员信息"
                }
            
            # 获取会员计划
            plan = MembershipPlan.query.get(membership.plan_id)
            if not plan:
                return {
                    "status": "error",
                    "message": "未找到会员计划信息"
                }
            
            # 计算使用情况
            today = datetime.datetime.utcnow().date()
            
            # 确保每日使用量重置
            if membership.last_essay_date != today:
                membership.essays_used_today = 0
                membership.last_essay_date = today
                db.session.commit()
            
            # 计算剩余可用量
            daily_limit = plan.max_essays_per_day
            daily_remaining = daily_limit - membership.essays_used_today if daily_limit > 0 else float('inf')
            
            total_limit = plan.max_essays_total
            total_remaining = total_limit - membership.essays_used_total if total_limit > 0 else float('inf')
            
            # 计算会员剩余天数
            days_remaining = (membership.end_date.date() - datetime.datetime.utcnow().date()).days
            
            # 查询用户过去30天的使用量
            thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
            essays = Essay.query.filter(
                Essay.user_id == user_id,
                Essay.created_at >= thirty_days_ago.timestamp()
            ).order_by(Essay.created_at).all()
            
            # 按日期分组统计
            daily_usage = defaultdict(int)
            for essay in essays:
                date_str = datetime.datetime.fromtimestamp(essay.created_at).strftime('%Y-%m-%d')
                daily_usage[date_str] += 1
            
            # 整理为时间序列
            usage_history = []
            current_date = thirty_days_ago.date()
            end_date = datetime.datetime.utcnow().date()
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                usage_history.append({
                    "date": date_str,
                    "count": daily_usage.get(date_str, 0)
                })
                current_date += datetime.timedelta(days=1)
            
            # 返回会员使用统计数据
            return {
                "status": "success",
                "user_id": user_id,
                "plan_name": plan.name,
                "plan_code": plan.code,
                "start_date": membership.start_date.isoformat(),
                "end_date": membership.end_date.isoformat(),
                "days_remaining": days_remaining,
                "is_active": membership.is_active and not membership.is_expired(),
                "usage_stats": {
                    "daily": {
                        "limit": daily_limit if daily_limit > 0 else "无限制",
                        "used": membership.essays_used_today,
                        "remaining": daily_remaining if daily_limit > 0 else "无限制",
                        "percentage": round(membership.essays_used_today / daily_limit * 100, 2) if daily_limit > 0 else 0
                    },
                    "total": {
                        "limit": total_limit if total_limit > 0 else "无限制",
                        "used": membership.essays_used_total,
                        "remaining": total_remaining if total_limit > 0 else "无限制",
                        "percentage": round(membership.essays_used_total / total_limit * 100, 2) if total_limit > 0 else 0
                    }
                },
                "usage_history": usage_history,
                "average_daily_usage": round(sum(item["count"] for item in usage_history) / len(usage_history), 2)
            }
            
        except Exception as e:
            logger.error(f"获取会员使用统计时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取会员使用统计失败: {str(e)}"
            }
    
    @staticmethod
    def get_membership_conversion_stats(period_days: int = 30) -> Dict[str, Any]:
        """
        获取会员转化率统计
        
        Args:
            period_days: 统计周期天数，默认30天
            
        Returns:
            Dict: 会员转化统计数据
        """
        try:
            # 计算统计起始时间
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=period_days)
            start_timestamp = start_date.timestamp()
            
            # 获取该时间段内的总注册用户数
            total_new_users = User.query.filter(User.created_at >= start_timestamp).count()
            
            # 获取该时间段内的付费会员数量
            paid_memberships = db.session.query(Membership).join(
                Subscription, Membership.id == Subscription.membership_id
            ).filter(
                Membership.created_at >= start_timestamp,
                Subscription.status == 'success'
            ).distinct(Membership.user_id).count()
            
            # 计算会员转化率
            conversion_rate = round(paid_memberships / total_new_users * 100, 2) if total_new_users > 0 else 0
            
            # 获取各计划的转化情况
            plan_conversions = db.session.query(
                MembershipPlan.code, MembershipPlan.name, func.count(Membership.id)
            ).join(
                Membership, MembershipPlan.id == Membership.plan_id
            ).join(
                Subscription, Membership.id == Subscription.membership_id
            ).filter(
                Membership.created_at >= start_timestamp,
                Subscription.status == 'success'
            ).group_by(
                MembershipPlan.id, MembershipPlan.code, MembershipPlan.name
            ).all()
            
            plan_stats = [
                {
                    "plan_code": code,
                    "plan_name": name,
                    "subscriptions": count,
                    "percentage": round(count / paid_memberships * 100, 2) if paid_memberships > 0 else 0
                }
                for code, name, count in plan_conversions
            ]
            
            # 按天分组统计新增会员
            daily_conversions = db.session.query(
                func.date(func.datetime(Membership.created_at, 'unixepoch')),
                func.count(Membership.id)
            ).join(
                Subscription, Membership.id == Subscription.membership_id
            ).filter(
                Membership.created_at >= start_timestamp,
                Subscription.status == 'success'
            ).group_by(
                func.date(func.datetime(Membership.created_at, 'unixepoch'))
            ).all()
            
            # 构建日期时间序列
            time_series = []
            current_date = start_date.date()
            end_date = datetime.datetime.utcnow().date()
            
            date_conversions = {date_str: count for date_str, count in daily_conversions}
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                time_series.append({
                    "date": date_str,
                    "new_memberships": date_conversions.get(date_str, 0)
                })
                current_date += datetime.timedelta(days=1)
            
            return {
                "status": "success",
                "period_days": period_days,
                "total_new_users": total_new_users,
                "total_new_memberships": paid_memberships,
                "conversion_rate": conversion_rate,
                "plan_statistics": plan_stats,
                "time_series": time_series
            }
            
        except Exception as e:
            logger.error(f"获取会员转化率统计时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取会员转化率统计失败: {str(e)}"
            }
    
    @staticmethod
    def get_membership_renewal_stats(period_days: int = 90) -> Dict[str, Any]:
        """
        获取会员续订率统计
        
        Args:
            period_days: 统计周期天数，默认90天
            
        Returns:
            Dict: 会员续订统计数据
        """
        try:
            # 计算统计起始时间
            start_date = datetime.datetime.utcnow() - datetime.timedelta(days=period_days)
            start_timestamp = start_date.timestamp()
            
            # 获取该时间段内到期的会员数量
            expired_memberships = Membership.query.filter(
                Membership.end_date >= start_date,
                Membership.end_date <= datetime.datetime.utcnow()
            ).count()
            
            # 获取已续费的会员数量
            renewed_memberships = db.session.query(Membership).join(
                Subscription, Membership.id == Subscription.membership_id
            ).filter(
                Membership.end_date >= start_date,
                Membership.end_date <= datetime.datetime.utcnow(),
                Subscription.created_at >= Membership.end_date.timestamp(),
                Subscription.status == 'success'
            ).distinct(Membership.user_id).count()
            
            # 计算续订率
            renewal_rate = round(renewed_memberships / expired_memberships * 100, 2) if expired_memberships > 0 else 0
            
            # 按计划分组统计续订率
            plan_renewals = db.session.query(
                MembershipPlan.code,
                MembershipPlan.name,
                func.count(Membership.id).label('expired'),
                func.sum(case((and_(
                    Subscription.created_at >= Membership.end_date.timestamp(),
                    Subscription.status == 'success'
                ), 1), else_=0)).label('renewed')
            ).join(
                Membership, MembershipPlan.id == Membership.plan_id
            ).outerjoin(
                Subscription, Membership.id == Subscription.membership_id
            ).filter(
                Membership.end_date >= start_date,
                Membership.end_date <= datetime.datetime.utcnow()
            ).group_by(
                MembershipPlan.id, MembershipPlan.code, MembershipPlan.name
            ).all()
            
            plan_stats = []
            for code, name, expired, renewed in plan_renewals:
                renewal_rate_plan = round(renewed / expired * 100, 2) if expired > 0 else 0
                plan_stats.append({
                    "plan_code": code,
                    "plan_name": name,
                    "expired": expired,
                    "renewed": renewed,
                    "renewal_rate": renewal_rate_plan
                })
            
            # 按月分组统计续订率
            monthly_renewals = db.session.query(
                func.strftime('%Y-%m', func.datetime(Membership.end_date, 'unixepoch')).label('month'),
                func.count(Membership.id).label('expired'),
                func.sum(case((and_(
                    Subscription.created_at >= Membership.end_date.timestamp(),
                    Subscription.status == 'success'
                ), 1), else_=0)).label('renewed')
            ).outerjoin(
                Subscription, Membership.id == Subscription.membership_id
            ).filter(
                Membership.end_date >= start_date,
                Membership.end_date <= datetime.datetime.utcnow()
            ).group_by('month').order_by('month').all()
            
            month_stats = []
            for month, expired, renewed in monthly_renewals:
                renewal_rate_month = round(renewed / expired * 100, 2) if expired > 0 else 0
                month_stats.append({
                    "month": month,
                    "expired": expired,
                    "renewed": renewed,
                    "renewal_rate": renewal_rate_month
                })
            
            return {
                "status": "success",
                "period_days": period_days,
                "total_expired_memberships": expired_memberships,
                "total_renewed_memberships": renewed_memberships,
                "overall_renewal_rate": renewal_rate,
                "plan_statistics": plan_stats,
                "monthly_statistics": month_stats
            }
            
        except Exception as e:
            logger.error(f"获取会员续订率统计时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取会员续订率统计失败: {str(e)}"
            }
    
    @staticmethod
    def get_membership_usage_predictions(user_id: int) -> Dict[str, Any]:
        """
        预测用户会员使用情况
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 会员使用预测数据
        """
        try:
            # 查询用户会员信息
            membership = Membership.query.filter_by(user_id=user_id).first()
            if not membership:
                return {
                    "status": "error",
                    "message": "未找到会员信息"
                }
            
            # 获取会员计划
            plan = MembershipPlan.query.get(membership.plan_id)
            if not plan:
                return {
                    "status": "error",
                    "message": "未找到会员计划信息"
                }
            
            # 计算会员剩余天数
            days_remaining = (membership.end_date.date() - datetime.datetime.utcnow().date()).days
            if days_remaining <= 0:
                return {
                    "status": "error",
                    "message": "会员已过期"
                }
            
            # 查询用户过去30天的使用量
            thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
            essays = Essay.query.filter(
                Essay.user_id == user_id,
                Essay.created_at >= thirty_days_ago.timestamp()
            ).order_by(Essay.created_at).all()
            
            # 计算每日平均使用量
            if len(essays) > 0:
                daily_avg_usage = len(essays) / 30
            else:
                daily_avg_usage = 0
            
            # 预测剩余会员期限内的总使用量
            predicted_total_usage = int(daily_avg_usage * days_remaining)
            
            # 计算是否会超出限制
            total_limit = plan.max_essays_total
            will_exceed_limit = False
            remaining_quota = 0
            
            if total_limit > 0:
                remaining_quota = total_limit - membership.essays_used_total
                will_exceed_limit = predicted_total_usage > remaining_quota
            
            # 计算预计用完配额的日期
            quota_completion_date = None
            if will_exceed_limit and daily_avg_usage > 0:
                days_until_completion = int(remaining_quota / daily_avg_usage)
                quota_completion_date = (datetime.datetime.utcnow() + datetime.timedelta(days=days_until_completion)).date().isoformat()
            
            # 返回预测结果
            return {
                "status": "success",
                "user_id": user_id,
                "plan_name": plan.name,
                "days_remaining": days_remaining,
                "daily_average_usage": round(daily_avg_usage, 2),
                "predicted_total_usage": predicted_total_usage,
                "total_remaining_quota": remaining_quota if total_limit > 0 else "无限制",
                "will_exceed_limit": will_exceed_limit,
                "quota_completion_date": quota_completion_date,
                "recommendation": "考虑升级会员计划" if will_exceed_limit else "当前会员计划足够使用"
            }
            
        except Exception as e:
            logger.error(f"获取会员使用预测时出错: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取会员使用预测失败: {str(e)}"
            } 