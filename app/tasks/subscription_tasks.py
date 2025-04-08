#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员订阅异步任务模块
处理会员订阅相关的后台任务，包括过期检查、续费通知等
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.tasks.celery_app import celery_app
from app.core.membership.membership_service import MembershipService
from app.core.subscription.subscription_service import SubscriptionService
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionStatus
from app.core.notification.notification_service import NotificationService
from app.models.db import db
from app.utils.date_util import format_date
from celery import shared_task
from app.models.membership import Membership
from app.tasks.user_tasks import send_notification_email

logger = logging.getLogger(__name__)

membership_service = MembershipService()
subscription_service = SubscriptionService()
notification_service = NotificationService()


@celery_app.task(name="subscription.process_subscription_task")
def process_subscription_task(subscription_id: int, action: str, **kwargs) -> Dict[str, Any]:
    """
    处理订阅相关的通用任务
    
    Args:
        subscription_id: 订阅ID
        action: 操作类型，如 'create', 'update', 'cancel', 'renew'
        **kwargs: 其他参数
    
    Returns:
        Dict: 处理结果
    """
    try:
        logger.info(f"处理订阅任务: subscription_id={subscription_id}, action={action}")
        
        result = {
            "status": "success",
            "subscription_id": subscription_id,
            "action": action,
            "message": f"订阅任务处理成功"
        }
        
        # 根据不同的操作类型执行不同的处理逻辑
        if action == "create":
            # 处理创建订阅后的操作
            user_id = kwargs.get("user_id")
            plan_id = kwargs.get("plan_id")
            
            # 发送欢迎邮件
            if user_id:
                user = User.query.get(user_id)
                if user and user.email:
                    notification_service.send_subscription_welcome_notification(
                        user_id=user.id,
                        email=user.email,
                        username=user.username,
                        subscription_id=subscription_id,
                        plan_id=plan_id
                    )
                    
            result["details"] = "创建订阅并发送欢迎通知"
            
        elif action == "update":
            # 处理更新订阅后的操作
            result["details"] = "更新订阅信息"
            
        elif action == "cancel":
            # 处理取消订阅后的操作
            cancel_reason = kwargs.get("reason", "用户取消")
            result["details"] = f"取消订阅，原因: {cancel_reason}"
            
        elif action == "renew":
            # 处理续订订阅的操作
            renewal_period = kwargs.get("period", 1)  # 默认续订1个月
            result["details"] = f"续订订阅 {renewal_period} 个月"
            
        else:
            result["status"] = "warning"
            result["message"] = f"未知的操作类型: {action}"
            
        logger.info(f"订阅任务处理完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"处理订阅任务时发生错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "subscription_id": subscription_id,
            "action": action,
            "message": f"处理订阅任务时发生错误: {str(e)}"
        }


@celery_app.task(name="subscription.check_expiring_subscriptions")
def check_expiring_subscriptions() -> Dict[str, Any]:
    """
    检查即将过期的会员订阅并发送通知
    
    Returns:
        Dict: 处理结果
    """
    try:
        logger.info("开始检查即将过期的会员订阅")
        
        # 获取当前日期
        now = datetime.now()
        
        # 查询3天内即将过期的活跃订阅
        expiring_date = now + timedelta(days=3)
        expiring_subscriptions = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.end_date <= expiring_date,
            Subscription.end_date > now,
            Subscription.auto_renew == False  # 只提醒没有开启自动续费的用户
        ).all()
        
        if not expiring_subscriptions:
            logger.info("没有即将过期的会员订阅")
            return {
                "status": "success",
                "message": "没有即将过期的会员订阅",
                "count": 0
            }
        
        # 发送过期提醒
        notified_count = 0
        
        for subscription in expiring_subscriptions:
            user = User.query.get(subscription.user_id)
            if not user or not user.email:
                continue
                
            # 计算剩余天数
            days_left = (subscription.end_date - now).days
            
            # 获取会员计划信息
            plan_info = subscription_service.get_plan_details(subscription.plan_id).get("plan", {})
            plan_name = plan_info.get("name", subscription.plan_id)
            
            # 发送邮件通知
            notification_result = notification_service.send_subscription_expiring_notification(
                user_id=user.id,
                email=user.email,
                username=user.username,
                subscription_id=subscription.id,
                plan_name=plan_name,
                expire_date=format_date(subscription.end_date, "%Y-%m-%d"),
                days_left=days_left
            )
            
            if notification_result.get("status") == "success":
                notified_count += 1
        
        logger.info(f"即将过期会员订阅检查完成，共发送{notified_count}条通知")
        
        return {
            "status": "success",
            "message": f"已发送{notified_count}条会员过期提醒",
            "total_count": len(expiring_subscriptions),
            "notified_count": notified_count
        }
        
    except Exception as e:
        logger.error(f"检查即将过期会员订阅时发生错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"检查即将过期会员订阅时发生错误: {str(e)}"
        }


@celery_app.task(name="subscription.process_expired_subscriptions")
def process_expired_subscriptions() -> Dict[str, Any]:
    """
    处理已过期的会员订阅
    
    Returns:
        Dict: 处理结果
    """
    try:
        logger.info("开始处理已过期的会员订阅")
        
        # 调用会员服务处理过期订阅
        result = membership_service.process_expired_subscriptions()
        
        if result.get("status") == "success":
            logger.info(f"会员订阅处理完成: {result.get('message')}")
        else:
            logger.error(f"会员订阅处理失败: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"处理过期会员订阅时发生错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"处理过期会员订阅时发生错误: {str(e)}"
        }


@celery_app.task(name="subscription.process_payment_retry")
def process_payment_retry() -> Dict[str, Any]:
    """
    处理自动续费支付失败的重试
    
    Returns:
        Dict: 处理结果
    """
    try:
        logger.info("开始处理自动续费支付失败的重试")
        
        # 获取当前日期和重试截止日期(3天内)
        now = datetime.now()
        retry_limit_date = now - timedelta(days=3)
        
        # 查询需要重试的自动续费记录
        failed_payments = Payment.query.join(Subscription).filter(
            Payment.status == PaymentStatus.FAILED.value,
            Payment.created_at >= retry_limit_date,
            Subscription.auto_renew == True
        ).all()
        
        if not failed_payments:
            logger.info("没有需要重试的自动续费记录")
            return {
                "status": "success",
                "message": "没有需要重试的自动续费记录",
                "count": 0
            }
        
        # 重试支付
        retry_count = 0
        success_count = 0
        
        for payment in failed_payments:
            # 检查是否超过重试次数
            retry_info = payment.notes or ""
            current_retries = retry_info.count("重试")
            
            if current_retries >= 3:
                logger.info(f"支付ID {payment.id} 已达到最大重试次数，跳过")
                continue
            
            # 重试支付
            from app.core.payment.payment_service import PaymentService
            payment_service = PaymentService()
            
            # 创建新的支付记录
            result = payment_service.create_payment(
                subscription_id=payment.subscription_id,
                payment_method=payment.payment_method
            )
            
            if result.get("status") == "success":
                # 更新原支付记录
                payment.notes = f"{retry_info} | 第{current_retries+1}次重试: 创建新支付 {result.get('payment_id')}"
                db.session.commit()
                
                success_count += 1
            
            retry_count += 1
        
        logger.info(f"支付重试处理完成，共重试{retry_count}笔支付，成功{success_count}笔")
        
        return {
            "status": "success",
            "message": f"支付重试处理完成",
            "total_count": len(failed_payments),
            "retry_count": retry_count,
            "success_count": success_count
        }
        
    except Exception as e:
        logger.error(f"处理自动续费支付重试时发生错误: {str(e)}", exc_info=True)
        if 'db_session' in locals():
            db.session.rollback()
        return {
            "status": "error",
            "message": f"处理自动续费支付重试时发生错误: {str(e)}"
        }


@celery_app.task(name="subscription.generate_subscription_report")
def generate_subscription_report(start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    """
    生成会员订阅报表
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    
    Returns:
        Dict: 报表生成结果
    """
    try:
        logger.info(f"开始生成会员订阅报表, 时间范围: {start_date} 至 {end_date}")
        
        # 设置默认日期范围（当前月）
        if not start_date or not end_date:
            now = datetime.now()
            start_date = datetime(now.year, now.month, 1).strftime('%Y-%m-%d')
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1)
            else:
                end_date = datetime(now.year, now.month + 1, 1)
            end_date = (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 解析日期
        from app.utils.date_util import parse_date
        start_datetime = parse_date(start_date, '%Y-%m-%d')
        end_datetime = parse_date(end_date, '%Y-%m-%d')
        
        if not start_datetime or not end_datetime:
            return {
                "status": "error",
                "message": "无效的日期格式，请使用YYYY-MM-DD格式"
            }
        
        # 调整结束日期为当天23:59:59
        from app.utils.date_util import get_end_of_day
        end_datetime = get_end_of_day(end_datetime)
        
        # 查询订阅数据
        # 1. 新增订阅
        new_subscriptions = Subscription.query.filter(
            Subscription.created_at >= start_datetime,
            Subscription.created_at <= end_datetime
        ).count()
        
        # 2. 已激活订阅
        active_subscriptions = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.start_date <= end_datetime
        ).count()
        
        # 3. 取消订阅
        canceled_subscriptions = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.CANCELED.value,
            Subscription.updated_at >= start_datetime,
            Subscription.updated_at <= end_datetime
        ).count()
        
        # 4. 过期订阅
        expired_subscriptions = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.EXPIRED.value,
            Subscription.end_date >= start_datetime,
            Subscription.end_date <= end_datetime
        ).count()
        
        # 5. 按计划类型统计
        plan_stats = {}
        for plan_id in ["basic", "premium"]:
            count = Subscription.query.filter(
                Subscription.plan_id == plan_id,
                Subscription.created_at >= start_datetime,
                Subscription.created_at <= end_datetime
            ).count()
            plan_stats[plan_id] = count
        
        # 6. 按支付方式统计
        payment_stats = {}
        payments = Payment.query.filter(
            Payment.status == PaymentStatus.SUCCESS.value,
            Payment.created_at >= start_datetime,
            Payment.created_at <= end_datetime
        ).all()
        
        for payment in payments:
            method = payment.payment_method
            if method not in payment_stats:
                payment_stats[method] = {
                    "count": 0,
                    "amount": 0
                }
            payment_stats[method]["count"] += 1
            payment_stats[method]["amount"] += payment.amount
        
        # 计算总收入
        total_revenue = sum(stats["amount"] for stats in payment_stats.values())
        
        # 保存报表数据
        report_data = {
            "start_date": start_date,
            "end_date": end_date,
            "new_subscriptions": new_subscriptions,
            "active_subscriptions": active_subscriptions,
            "canceled_subscriptions": canceled_subscriptions,
            "expired_subscriptions": expired_subscriptions,
            "plan_stats": plan_stats,
            "payment_stats": payment_stats,
            "total_revenue": total_revenue,
            "report_generated_at": datetime.now().isoformat()
        }
        
        # 这里可以将报表保存到数据库或者文件系统
        # 示例: 保存为JSON文件
        import json
        import os
        
        report_dir = "reports/subscription"
        os.makedirs(report_dir, exist_ok=True)
        
        report_filename = f"{report_dir}/subscription_report_{start_date}_{end_date}.json"
        with open(report_filename, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"会员订阅报表已生成: {report_filename}")
        
        return {
            "status": "success",
            "message": "会员订阅报表已生成",
            "report_data": report_data,
            "report_file": report_filename
        }
        
    except Exception as e:
        logger.error(f"生成会员订阅报表时发生错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"生成会员订阅报表时发生错误: {str(e)}"
        }


@shared_task(name="tasks.send_subscription_renewal_reminders")
def send_subscription_renewal_reminders(days_before_expiry: int = 7):
    """
    检查即将到期的会员订阅并发送续订提醒。

    Args:
        days_before_expiry: 提前多少天发送提醒。
    """
    logger.info(f"开始检查 {days_before_expiry} 天内到期的会员订阅...")
    try:
        # 计算目标到期日期范围
        today = datetime.utcnow().date()
        reminder_date_start = today + timedelta(days=days_before_expiry)
        # 可能需要稍微放宽结束日期以覆盖当天到期的情况
        reminder_date_end = reminder_date_start + timedelta(days=1) 

        # 查询即将到期的有效会员资格
        # 注意：这里的查询逻辑依赖于 Membership 和 Subscription 模型的具体设计
        # 假设 Membership 存储了会员状态和到期日期
        expiring_memberships = Membership.query.filter(
            Membership.is_active == True,
            Membership.end_date >= reminder_date_start,
            Membership.end_date < reminder_date_end,
            # 可选：排除已经自动续订或已取消的用户
            # Membership.auto_renew == False, 
            # Membership.status != 'cancelled'
        ).all()

        if not expiring_memberships:
            logger.info("没有找到即将到期的会员订阅。")
            return {"status": "success", "message": "没有需要发送的提醒", "reminders_sent": 0}

        sent_count = 0
        failed_count = 0
        for membership in expiring_memberships:
            try:
                user = User.query.get(membership.user_id)
                if not user or not user.email:
                    logger.warning(f"会员 {membership.id} (用户 {membership.user_id}) 缺少用户信息或邮箱，无法发送提醒。")
                    continue

                # 准备邮件内容
                subject = f"您的会员即将于 {membership.end_date.strftime('%Y-%m-%d')} 到期提醒"
                # 可以创建一个更丰富的HTML模板
                body = f"尊敬的 {user.username}，\n\n您的会员资格即将于 {membership.end_date.strftime('%Y-%m-%d')} 到期。"
                body += "为了确保您能继续享受会员权益，请及时续订。\n\n感谢您的支持！"

                # 异步发送邮件
                send_notification_email.delay(user.email, subject, body)
                logger.info(f"已为用户 {user.id} ({user.email}) 创建续订提醒邮件任务，会员到期日: {membership.end_date.strftime('%Y-%m-%d')}")
                sent_count += 1

            except Exception as e:
                logger.error(f"为会员 {membership.id} (用户 {membership.user_id}) 发送提醒时出错: {e}", exc_info=True)
                failed_count += 1
        
        logger.info(f"会员续订提醒任务完成：成功发送 {sent_count} 封，失败 {failed_count} 封。")
        return {
            "status": "success", 
            "message": f"提醒发送完成", 
            "reminders_sent": sent_count, 
            "failures": failed_count
        }

    except Exception as e:
        logger.error(f"执行会员续订提醒任务时发生严重错误: {e}", exc_info=True)
        return {"status": "error", "message": f"任务执行失败: {str(e)}"}


@celery_app.task(name="subscription.optimize_renewal_offers")
def optimize_renewal_offers():
    """
    优化会员续费方案
    基于用户历史使用数据，为不同用户推荐个性化续费方案
    """
    try:
        logger.info("开始执行会员续费方案优化任务")
        
        # 获取当前时间
        now = datetime.now()
        
        # 找出30天内即将到期的会员
        target_date = now + timedelta(days=30)
        expiring_memberships = Membership.query.filter(
            Membership.end_date <= target_date,
            Membership.is_active == True,
            Membership.is_auto_renew == False
        ).all()
        
        logger.info(f"找到 {len(expiring_memberships)} 个30天内即将到期的会员")
        
        # 会员计划列表
        all_plans = MembershipPlan.query.filter_by(is_active=True).order_by(MembershipPlan.price).all()
        
        for membership in expiring_memberships:
            user = User.query.get(membership.user_id)
            if not user:
                continue
            
            current_plan = MembershipPlan.query.get(membership.plan_id)
            if not current_plan:
                continue
            
            # 分析用户使用模式
            try:
                # 获取过去90天的使用数据
                ninety_days_ago = now - timedelta(days=90)
                user_essays = Essay.query.filter(
                    Essay.user_id == user.id,
                    Essay.created_at >= ninety_days_ago.timestamp()
                ).all()
                
                # 如果没有使用记录，跳过优化
                if not user_essays:
                    continue
                
                # 计算平均每日用量和高峰日使用量
                daily_usage = {}
                for essay in user_essays:
                    date_key = datetime.fromtimestamp(essay.created_at).strftime('%Y-%m-%d')
                    daily_usage[date_key] = daily_usage.get(date_key, 0) + 1
                
                avg_daily_usage = len(user_essays) / 90
                max_daily_usage = max(daily_usage.values()) if daily_usage else 0
                
                # 确定用户活跃度
                active_days = len(daily_usage)
                activity_level = "高" if active_days > 45 else "中" if active_days > 15 else "低"
                
                # 推荐合适的会员计划
                recommended_plan = None
                upgrade_recommended = False
                downgrade_recommended = False
                
                for plan in all_plans:
                    # 如果平均使用量接近当前计划限制的80%，推荐升级
                    if plan.max_essays_per_day > 0 and avg_daily_usage >= plan.max_essays_per_day * 0.8:
                        continue
                    
                    # 如果高峰使用量超过计划限制，也不适合
                    if plan.max_essays_per_day > 0 and max_daily_usage > plan.max_essays_per_day:
                        continue
                    
                    # 找到适合的计划
                    recommended_plan = plan
                    
                    # 判断是升级还是降级
                    if plan.price > current_plan.price:
                        upgrade_recommended = True
                    elif plan.price < current_plan.price:
                        downgrade_recommended = True
                    
                    break
                
                # 如果没有找到更好的计划，就推荐续订当前计划
                if not recommended_plan:
                    recommended_plan = current_plan
                
                # 根据用户活跃度和使用模式，选择个性化的优惠策略
                discount_percent = 0
                offer_months = 0
                
                if activity_level == "高":
                    # 高活跃度用户，提供更多优惠以提高留存
                    discount_percent = 15 if upgrade_recommended else 10
                    offer_months = 12  # 推荐年付
                elif activity_level == "中":
                    discount_percent = 10 if upgrade_recommended else 5
                    offer_months = 6  # 推荐半年付
                else:  # 低活跃度
                    discount_percent = 5
                    offer_months = 3  # 推荐季付
                
                # 创建个性化续费推荐
                from app.models.notification import Notification
                
                # 设置到期剩余天数
                days_remaining = (membership.end_date - now).days
                
                # 根据不同情况设置不同的消息
                if days_remaining <= 7:
                    urgency = "高"
                    title = f"专属优惠：续订{recommended_plan.name}立享{discount_percent}%折扣"
                elif days_remaining <= 15:
                    urgency = "中"
                    title = f"为您推荐：{offer_months}个月{recommended_plan.name}会员优惠"
                else:
                    urgency = "低"
                    title = f"会员续费规划：基于您的使用习惯推荐"
                
                # 构建推荐内容
                content = f"根据您的使用习惯分析，我们为您推荐{recommended_plan.name}会员"
                if upgrade_recommended:
                    content += f"（升级），每日可批改{recommended_plan.max_essays_per_day}篇作文"
                elif downgrade_recommended:
                    content += f"（调整），每日可批改{recommended_plan.max_essays_per_day}篇作文，更经济实惠"
                else:
                    content += f"（续订），继续享受每日{recommended_plan.max_essays_per_day}篇作文批改"
                
                content += f"。现在续订{offer_months}个月，立享{discount_percent}%折扣优惠！"
                
                # 创建通知
                Notification.create(
                    user_id=user.id,
                    type="renewal_offer",
                    title=title,
                    content=content,
                    metadata={
                        "recommended_plan": {
                            "id": recommended_plan.id,
                            "code": recommended_plan.code,
                            "name": recommended_plan.name,
                            "price": recommended_plan.price
                        },
                        "current_plan": {
                            "id": current_plan.id,
                            "code": current_plan.code,
                            "name": current_plan.name,
                            "price": current_plan.price
                        },
                        "discount_percent": discount_percent,
                        "offer_months": offer_months,
                        "days_remaining": days_remaining,
                        "urgency": urgency,
                        "usage_stats": {
                            "avg_daily_usage": avg_daily_usage,
                            "max_daily_usage": max_daily_usage,
                            "active_days": active_days,
                            "activity_level": activity_level
                        }
                    }
                )
                
                logger.info(f"为用户 {user.username}({user.id}) 创建了个性化续费推荐")
                
            except Exception as e:
                logger.error(f"为用户 {user.id} 优化续费方案时出错: {str(e)}", exc_info=True)
                continue
        
        logger.info("会员续费方案优化任务执行完成")
        return {
            "status": "success",
            "message": "会员续费方案优化任务执行完成"
        }
        
    except Exception as e:
        logger.error(f"执行会员续费方案优化任务时出错: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"执行会员续费方案优化任务失败: {str(e)}"
        }


@celery_app.task(name="subscription.analyze_subscription_churn")
def analyze_subscription_churn():
    """
    分析会员流失情况
    识别流失风险高的会员并提供干预策略
    """
    try:
        logger.info("开始执行会员流失分析任务")
        
        # 获取当前时间
        now = datetime.now()
        
        # 计算近期（30天）的流失率
        thirty_days_ago = now - timedelta(days=30)
        start_timestamp = thirty_days_ago.timestamp()
        
        # 获取30天前活跃的会员总数
        active_members_30days_ago = db.session.query(Membership).filter(
            Membership.is_active == True,
            Membership.created_at < start_timestamp,
            Membership.end_date > thirty_days_ago
        ).count()
        
        # 获取这些会员中已流失的数量（未续费）
        churned_members = db.session.query(Membership).filter(
            Membership.is_active == False,
            Membership.created_at < start_timestamp,
            Membership.end_date.between(thirty_days_ago, now),
            ~db.session.exists().where(
                Subscription.membership_id == Membership.id,
                Subscription.created_at > Membership.end_date.timestamp(),
                Subscription.status == 'success'
            )
        ).count()
        
        # 计算流失率
        churn_rate = (churned_members / active_members_30days_ago) * 100 if active_members_30days_ago > 0 else 0
        
        # 按会员计划分组统计流失率
        plan_churn_rates = []
        all_plans = MembershipPlan.query.all()
        
        for plan in all_plans:
            plan_members_30days_ago = db.session.query(Membership).filter(
                Membership.is_active == True,
                Membership.created_at < start_timestamp,
                Membership.end_date > thirty_days_ago,
                Membership.plan_id == plan.id
            ).count()
            
            plan_churned_members = db.session.query(Membership).filter(
                Membership.is_active == False,
                Membership.created_at < start_timestamp,
                Membership.end_date.between(thirty_days_ago, now),
                Membership.plan_id == plan.id,
                ~db.session.exists().where(
                    Subscription.membership_id == Membership.id,
                    Subscription.created_at > Membership.end_date.timestamp(),
                    Subscription.status == 'success'
                )
            ).count()
            
            plan_churn_rate = (plan_churned_members / plan_members_30days_ago) * 100 if plan_members_30days_ago > 0 else 0
            
            plan_churn_rates.append({
                "plan_id": plan.id,
                "plan_code": plan.code,
                "plan_name": plan.name,
                "members_count": plan_members_30days_ago,
                "churned_count": plan_churned_members,
                "churn_rate": round(plan_churn_rate, 2)
            })
        
        # 找出流失风险高的会员
        # 风险因素：
        # 1. 近30天使用频率明显下降的会员
        # 2. 会员即将到期（30天内）且未设置自动续费的会员
        # 3. 最近一次续费时有延迟的会员（可能在犹豫）
        at_risk_members = []
        
        # 获取即将在30天内到期的会员
        expiring_soon = db.session.query(Membership).filter(
            Membership.is_active == True,
            Membership.end_date.between(now, now + timedelta(days=30)),
            Membership.is_auto_renew == False
        ).all()
        
        for membership in expiring_soon:
            user = User.query.get(membership.user_id)
            if not user:
                continue
            
            plan = MembershipPlan.query.get(membership.plan_id)
            if not plan:
                continue
            
            # 分析使用频率变化
            recent_period = db.session.query(db.session.func.count(Essay.id)).filter(
                Essay.user_id == user.id,
                Essay.created_at.between(
                    (now - timedelta(days=30)).timestamp(),
                    now.timestamp()
                )
            ).scalar()
            
            previous_period = db.session.query(db.session.func.count(Essay.id)).filter(
                Essay.user_id == user.id,
                Essay.created_at.between(
                    (now - timedelta(days=60)).timestamp(),
                    (now - timedelta(days=30)).timestamp()
                )
            ).scalar()
            
            # 计算使用频率变化率，避免除以零
            usage_change_rate = 0
            if previous_period > 0:
                usage_change_rate = ((recent_period - previous_period) / previous_period) * 100
            
            # 获取用户上次续费情况
            last_renewal = db.session.query(Subscription).filter(
                Subscription.membership_id == membership.id,
                Subscription.status == 'success'
            ).order_by(db.session.desc(Subscription.created_at)).first()
            
            # 计算上次续费是否有延迟
            renewal_delay = 0
            if last_renewal and last_renewal.created_at > membership.start_date.timestamp():
                renewal_delay = (datetime.fromtimestamp(last_renewal.created_at) - membership.start_date).days
            
            # 计算流失风险分数（0-100）
            # 使用频率下降50%或以上：+50分
            # 未设置自动续费：+20分
            # 上次续费有延迟：每延迟1天+2分，最高+30分
            risk_score = 0
            
            if usage_change_rate <= -50:
                risk_score += 50
            elif usage_change_rate <= -30:
                risk_score += 30
            elif usage_change_rate <= -10:
                risk_score += 10
            
            if not membership.is_auto_renew:
                risk_score += 20
            
            if renewal_delay > 0:
                risk_score += min(renewal_delay * 2, 30)
            
            # 根据用户活跃度再调整分数
            if recent_period == 0:  # 最近30天完全没有使用
                risk_score += 50
            elif recent_period < 3:  # 最近30天使用很少
                risk_score += 20
            
            # 风险系数大于50的视为高风险
            if risk_score >= 50:
                # 根据风险情况设计不同的干预策略
                intervention_strategy = "no_action"
                discount_offer = 0
                
                if risk_score >= 80:
                    # 高风险：提供较大折扣和个性化内容
                    intervention_strategy = "high_discount_personalized"
                    discount_offer = 25
                elif risk_score >= 65:
                    # 中高风险：提供中等折扣
                    intervention_strategy = "medium_discount"
                    discount_offer = 15
                elif risk_score >= 50:
                    # 中等风险：提供小折扣并强调价值
                    intervention_strategy = "small_discount_value"
                    discount_offer = 10
                
                # 添加到风险列表
                at_risk_members.append({
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "membership_id": membership.id,
                    "plan_name": plan.name,
                    "end_date": membership.end_date.isoformat(),
                    "days_remaining": (membership.end_date - now).days,
                    "usage_change_rate": round(usage_change_rate, 2),
                    "recent_usage": recent_period,
                    "previous_usage": previous_period,
                    "renewal_delay": renewal_delay,
                    "risk_score": risk_score,
                    "intervention_strategy": intervention_strategy,
                    "discount_offer": discount_offer
                })
                
                # 为高风险用户创建干预通知
                if intervention_strategy != "no_action":
                    from app.models.notification import Notification
                    
                    title = "我们想念您的使用"
                    content = f"我们注意到您的{plan.name}会员将在{(membership.end_date - now).days}天后到期。"
                    
                    if intervention_strategy == "high_discount_personalized":
                        title = f"专属优惠：为您提供{discount_offer}%的续费折扣"
                        content += f"为了感谢您的支持，我们特别为您提供{discount_offer}%的续费折扣。同时，我们会根据您的使用习惯，为您推荐最适合的内容和功能。"
                    elif intervention_strategy == "medium_discount":
                        title = f"会员续费优惠：享受{discount_offer}%折扣"
                        content += f"为了感谢您的支持，我们为您提供{discount_offer}%的续费折扣。不要错过这个机会！"
                    elif intervention_strategy == "small_discount_value":
                        title = f"会员续费提醒：享受{discount_offer}%折扣"
                        content += f"为了让您继续享受高质量的作文批改服务，我们为您提供{discount_offer}%的续费折扣。"
                    
                    # 创建通知
                    Notification.create(
                        user_id=user.id,
                        type="churn_prevention",
                        title=title,
                        content=content,
                        metadata={
                            "risk_score": risk_score,
                            "intervention_strategy": intervention_strategy,
                            "discount_offer": discount_offer,
                            "days_remaining": (membership.end_date - now).days
                        }
                    )
                    
                    logger.info(f"为高风险流失用户 {user.username}({user.id}) 创建了干预通知")
        
        # 保存分析报告
        report_dir = Path(config.BACKUP_CONFIG.get('reports_dir', 'reports')) / 'churn'
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"churn_analysis_{now.strftime('%Y%m%d')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "date": now.isoformat(),
                "overall_churn_rate": round(churn_rate, 2),
                "active_members_count": active_members_30days_ago,
                "churned_members_count": churned_members,
                "plan_churn_rates": plan_churn_rates,
                "at_risk_members_count": len(at_risk_members),
                "at_risk_members": at_risk_members
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"会员流失分析完成，报告已保存至 {report_file}")
        
        # 如果流失率超过警戒阈值，发送警报邮件给管理员
        alert_threshold = config.MEMBERSHIP_CONFIG.get('churn_alert_threshold', 10)  # 默认10%
        if churn_rate > alert_threshold:
            admin_emails = config.APP_CONFIG.get('admin_emails', [])
            if admin_emails:
                from app.utils.email_service import send_email
                send_email(
                    to_email=admin_emails[0],
                    cc_emails=admin_emails[1:] if len(admin_emails) > 1 else None,
                    subject=f"【警报】会员流失率异常 - {round(churn_rate, 2)}%",
                    template="admin_churn_alert.html",
                    template_params={
                        "churn_rate": round(churn_rate, 2),
                        "alert_threshold": alert_threshold,
                        "date": now.strftime("%Y-%m-%d"),
                        "active_members": active_members_30days_ago,
                        "churned_members": churned_members,
                        "at_risk_members_count": len(at_risk_members),
                        "plan_churn_rates": plan_churn_rates,
                        "report_url": f"{config.APP_CONFIG.get('admin_base_url')}/reports/churn/{now.strftime('%Y%m%d')}"
                    }
                )
                logger.info(f"已发送流失率警报邮件给管理员")
        
        return {
            "status": "success",
            "message": "会员流失分析任务执行完成",
            "churn_rate": round(churn_rate, 2),
            "at_risk_members_count": len(at_risk_members),
            "report_file": str(report_file)
        }
        
    except Exception as e:
        logger.error(f"执行会员流失分析任务时出错: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"执行会员流失分析任务失败: {str(e)}"
        }


@celery_app.task(name="subscription.renew_expiring_subscriptions")
def renew_expiring_subscriptions() -> Dict[str, Any]:
    """
    自动续订即将到期的订阅
    
    Returns:
        Dict: 处理结果
    """
    try:
        logger.info("开始处理即将过期的自动续订会员")
        
        # 获取当前日期和到期日期范围（1天内）
        now = datetime.now()
        expiry_date = now + timedelta(days=1)
        
        # 查询即将到期且已开启自动续订的订阅
        auto_renew_subscriptions = Subscription.query.filter(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.end_date <= expiry_date,
            Subscription.end_date > now,
            Subscription.auto_renew == True
        ).all()
        
        if not auto_renew_subscriptions:
            logger.info("没有需要自动续订的会员")
            return {
                "status": "success",
                "message": "没有需要自动续订的会员",
                "count": 0
            }
        
        # 处理自动续订
        renewal_count = 0
        success_count = 0
        
        for subscription in auto_renew_subscriptions:
            logger.info(f"处理订阅 {subscription.id} 的自动续订")
            
            # 获取用户信息
            user = User.query.get(subscription.user_id)
            if not user:
                logger.error(f"找不到订阅 {subscription.id} 对应的用户 {subscription.user_id}")
                continue
            
            # 使用订阅服务执行续订
            from app.core.payment.payment_service import PaymentService
            payment_service = PaymentService()
            
            # 创建续订支付
            result = payment_service.create_renewal_payment(
                subscription_id=subscription.id,
                payment_method=subscription.last_payment_method or "default"
            )
            
            renewal_count += 1
            
            if result.get("status") == "success":
                success_count += 1
                
                # 更新续订记录
                subscription.last_renewal_attempt = now
                subscription.renewal_status = "pending"
                db.session.commit()
                
                # 发送续订通知
                notification_service.send_subscription_renewal_notification(
                    user_id=user.id,
                    email=user.email,
                    username=user.username,
                    subscription_id=subscription.id,
                    payment_id=result.get("payment_id")
                )
            else:
                # 记录续订失败
                subscription.last_renewal_attempt = now
                subscription.renewal_status = "failed"
                subscription.renewal_notes = result.get("message", "支付创建失败")
                db.session.commit()
        
        logger.info(f"自动续订处理完成，共处理{renewal_count}个订阅，成功{success_count}个")
        
        return {
            "status": "success",
            "message": f"自动续订处理完成",
            "total_count": len(auto_renew_subscriptions),
            "renewal_count": renewal_count,
            "success_count": success_count
        }
        
    except Exception as e:
        logger.error(f"处理自动续订时发生错误: {str(e)}", exc_info=True)
        if 'db_session' in locals():
            db.session.rollback()
        return {
            "status": "error",
            "message": f"处理自动续订时发生错误: {str(e)}"
        } 