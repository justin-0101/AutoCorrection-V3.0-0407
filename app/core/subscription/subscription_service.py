#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
订阅服务模块
处理用户会员订阅的管理
"""

import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import or_, and_

from app.config import config
from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.payment import Payment, PaymentStatus
from app.core.payment.payment_service import PaymentService
from app.models.db import db
from app.utils.date_util import add_months, format_date

logger = logging.getLogger(__name__)

class SubscriptionService:
    """订阅服务，处理会员订阅管理"""
    
    def __init__(self):
        """初始化订阅服务"""
        self.payment_service = PaymentService()
        self.membership_config = config.MEMBERSHIP_CONFIG
        
    def get_plans(self) -> List[Dict[str, Any]]:
        """
        获取可用的会员计划
        
        Returns:
            List[Dict]: 会员计划列表
        """
        try:
            plans = []
            
            # 从配置中获取会员计划
            for plan_id, plan_data in self.membership_config.get("plans", {}).items():
                if plan_id == "free":
                    continue
                    
                plan = {
                    "id": plan_id,
                    "name": plan_data.get("name", ""),
                    "description": plan_data.get("description", ""),
                    "level": plan_data.get("level", ""),
                    "price_monthly": plan_data.get("price_monthly", 0),
                    "price_yearly": plan_data.get("price_yearly", 0),
                    "discount": self._calculate_discount(
                        plan_data.get("price_monthly", 0),
                        plan_data.get("price_yearly", 0)
                    ),
                    "features": plan_data.get("features", []),
                    "essay_limit_daily": plan_data.get("essay_limit_daily", 0),
                    "essay_limit_monthly": plan_data.get("essay_limit_monthly", 0),
                    "highlight": plan_data.get("highlight", False)
                }
                
                plans.append(plan)
                
            return plans
            
        except Exception as e:
            logger.error(f"获取会员计划时发生错误: {str(e)}", exc_info=True)
            return []
    
    def get_plan_details(self, plan_id: str) -> Dict[str, Any]:
        """
        获取指定会员计划的详情
        
        Args:
            plan_id: 计划ID
            
        Returns:
            Dict: 计划详情
        """
        try:
            plan_data = self.membership_config.get("plans", {}).get(plan_id)
            
            if not plan_data:
                return {
                    "status": "error",
                    "message": f"未找到计划: {plan_id}"
                }
                
            plan = {
                "id": plan_id,
                "name": plan_data.get("name", ""),
                "description": plan_data.get("description", ""),
                "level": plan_data.get("level", ""),
                "price_monthly": plan_data.get("price_monthly", 0),
                "price_yearly": plan_data.get("price_yearly", 0),
                "discount": self._calculate_discount(
                    plan_data.get("price_monthly", 0),
                    plan_data.get("price_yearly", 0)
                ),
                "features": plan_data.get("features", []),
                "essay_limit_daily": plan_data.get("essay_limit_daily", 0),
                "essay_limit_monthly": plan_data.get("essay_limit_monthly", 0),
                "highlight": plan_data.get("highlight", False)
            }
            
            return {
                "status": "success",
                "plan": plan
            }
            
        except Exception as e:
            logger.error(f"获取计划详情时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取计划详情时发生错误: {str(e)}"
            }
    
    def create_subscription(self, user_id: int, plan_id: str, duration: str) -> Dict[str, Any]:
        """
        创建订阅
        
        Args:
            user_id: 用户ID
            plan_id: 计划ID
            duration: 订阅时长（monthly/yearly）
            
        Returns:
            Dict: 创建结果
        """
        try:
            # 检查用户
            user = db.session.query(User).filter_by(id=user_id).first()
            if not user:
                return {
                    "status": "error",
                    "message": "用户不存在"
                }
                
            # 检查计划
            plan_data = self.membership_config.get("plans", {}).get(plan_id)
            if not plan_data or plan_id == "free":
                return {
                    "status": "error",
                    "message": f"无效的会员计划: {plan_id}"
                }
                
            # 检查订阅时长
            if duration not in ["monthly", "yearly"]:
                return {
                    "status": "error",
                    "message": f"无效的订阅时长: {duration}"
                }
                
            # 获取价格
            price_field = f"price_{duration}"
            price = plan_data.get(price_field, 0)
            
            if price <= 0:
                return {
                    "status": "error",
                    "message": f"计划价格无效: {price}"
                }
                
            # 检查是否有未完成的订阅
            existing_subscription = db.session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.PENDING.value
            ).first()
            
            if existing_subscription:
                return {
                    "status": "error",
                    "message": "已有未完成的订阅，请先完成支付或取消"
                }
                
            # 创建新订阅
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                price=price,
                status=SubscriptionStatus.PENDING.value,
                duration=duration,
                auto_renew=True  # 默认开启自动续费
            )
            
            db.session.add(subscription)
            db.session.commit()
            
            return {
                "status": "success",
                "message": "订阅创建成功",
                "subscription_id": subscription.id,
                "plan_id": plan_id,
                "duration": duration,
                "price": price
            }
            
        except Exception as e:
            logger.error(f"创建订阅时发生错误: {str(e)}", exc_info=True)
            if 'db_session' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"创建订阅时发生错误: {str(e)}"
            }
    
    def pay_subscription(self, subscription_id: int, payment_method: str) -> Dict[str, Any]:
        """
        支付订阅
        
        Args:
            subscription_id: 订阅ID
            payment_method: 支付方式
            
        Returns:
            Dict: 支付结果
        """
        try:
            # 创建支付
            result = self.payment_service.create_payment(subscription_id, payment_method)
            return result
            
        except Exception as e:
            logger.error(f"支付订阅时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"支付订阅时发生错误: {str(e)}"
            }
    
    def cancel_subscription(self, user_id: int, subscription_id: int) -> Dict[str, Any]:
        """
        取消订阅
        
        Args:
            user_id: 用户ID
            subscription_id: 订阅ID
            
        Returns:
            Dict: 取消结果
        """
        try:
            # 检查订阅
            subscription = db.session.query(Subscription).filter_by(id=subscription_id).first()
            
            if not subscription:
                return {
                    "status": "error",
                    "message": "订阅不存在"
                }
                
            # 检查权限
            if subscription.user_id != user_id:
                return {
                    "status": "error",
                    "message": "无权操作此订阅"
                }
                
            # 检查订阅状态
            if subscription.status == SubscriptionStatus.CANCELED.value:
                return {
                    "status": "success",
                    "message": "订阅已取消"
                }
                
            if subscription.status == SubscriptionStatus.ACTIVE.value:
                # 关闭自动续费
                subscription.auto_renew = False
                subscription.updated_at = datetime.datetime.now()
                db.session.commit()
                
                return {
                    "status": "success",
                    "message": "自动续费已关闭，当前订阅将在到期后终止",
                    "end_date": format_date(subscription.end_date) if subscription.end_date else None
                }
                
            elif subscription.status == SubscriptionStatus.PENDING.value:
                # 取消未支付的订阅
                subscription.status = SubscriptionStatus.CANCELED.value
                subscription.updated_at = datetime.datetime.now()
                
                # 取消相关未支付的订单
                payments = db.session.query(Payment).filter(
                    Payment.subscription_id == subscription_id,
                    Payment.status == PaymentStatus.PENDING.value
                ).all()
                
                for payment in payments:
                    self.payment_service.cancel_payment(payment.id)
                
                db.session.commit()
                
                return {
                    "status": "success",
                    "message": "订阅已取消"
                }
                
            else:
                return {
                    "status": "error",
                    "message": f"订阅状态为{subscription.status}，无法取消"
                }
                
        except Exception as e:
            logger.error(f"取消订阅时发生错误: {str(e)}", exc_info=True)
            if 'db_session' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"取消订阅时发生错误: {str(e)}"
            }
    
    def toggle_auto_renew(self, user_id: int, subscription_id: int) -> Dict[str, Any]:
        """
        切换自动续费状态
        
        Args:
            user_id: 用户ID
            subscription_id: 订阅ID
            
        Returns:
            Dict: 切换结果
        """
        try:
            # 检查订阅
            subscription = db.session.query(Subscription).filter_by(id=subscription_id).first()
            
            if not subscription:
                return {
                    "status": "error",
                    "message": "订阅不存在"
                }
                
            # 检查权限
            if subscription.user_id != user_id:
                return {
                    "status": "error",
                    "message": "无权操作此订阅"
                }
                
            # 检查订阅状态
            if subscription.status != SubscriptionStatus.ACTIVE.value:
                return {
                    "status": "error",
                    "message": f"订阅状态为{subscription.status}，无法更改自动续费设置"
                }
                
            # 切换自动续费状态
            subscription.auto_renew = not subscription.auto_renew
            subscription.updated_at = datetime.datetime.now()
            
            db.session.commit()
            
            return {
                "status": "success",
                "message": f"自动续费已{'开启' if subscription.auto_renew else '关闭'}",
                "auto_renew": subscription.auto_renew
            }
            
        except Exception as e:
            logger.error(f"切换自动续费状态时发生错误: {str(e)}", exc_info=True)
            if 'db_session' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"切换自动续费状态时发生错误: {str(e)}"
            }
    
    def get_user_subscriptions(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户的订阅记录
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户订阅记录
        """
        try:
            # 获取用户
            user = db.session.query(User).filter_by(id=user_id).first()
            if not user:
                return {
                    "status": "error",
                    "message": "用户不存在"
                }
                
            # 获取当前有效订阅
            active_subscription = db.session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value
            ).first()
            
            # 获取历史订阅
            history_subscriptions = db.session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status != SubscriptionStatus.PENDING.value
            ).order_by(Subscription.created_at.desc()).all()
            
            # 格式化订阅数据
            subscriptions = []
            for sub in history_subscriptions:
                plan_data = self.membership_config.get("plans", {}).get(sub.plan_id, {})
                
                subscriptions.append({
                    "id": sub.id,
                    "plan_id": sub.plan_id,
                    "plan_name": plan_data.get("name", sub.plan_id),
                    "status": sub.status,
                    "price": sub.price,
                    "duration": sub.duration,
                    "start_date": format_date(sub.start_date) if sub.start_date else None,
                    "end_date": format_date(sub.end_date) if sub.end_date else None,
                    "auto_renew": sub.auto_renew,
                    "created_at": format_date(sub.created_at)
                })
            
            # 获取待支付订阅
            pending_subscription = db.session.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.PENDING.value
            ).first()
            
            return {
                "status": "success",
                "membership_level": user.membership_level,
                "membership_expires": format_date(user.membership_expires) if user.membership_expires else None,
                "active_subscription": self._format_subscription(active_subscription) if active_subscription else None,
                "pending_subscription": self._format_subscription(pending_subscription) if pending_subscription else None,
                "subscriptions": subscriptions
            }
            
        except Exception as e:
            logger.error(f"获取用户订阅时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取用户订阅时发生错误: {str(e)}"
            }
    
    def get_subscription_details(self, user_id: int, subscription_id: int) -> Dict[str, Any]:
        """
        获取订阅详情
        
        Args:
            user_id: 用户ID
            subscription_id: 订阅ID
            
        Returns:
            Dict: 订阅详情
        """
        try:
            # 检查订阅
            subscription = db.session.query(Subscription).filter_by(id=subscription_id).first()
            
            if not subscription:
                return {
                    "status": "error",
                    "message": "订阅不存在"
                }
                
            # 检查权限
            if subscription.user_id != user_id:
                return {
                    "status": "error",
                    "message": "无权查看此订阅"
                }
                
            # 获取支付记录
            payments = db.session.query(Payment).filter(
                Payment.subscription_id == subscription_id
            ).order_by(Payment.created_at.desc()).all()
            
            payment_records = []
            for payment in payments:
                payment_records.append({
                    "id": payment.id,
                    "order_id": payment.order_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "status": payment.status,
                    "payment_method": payment.payment_method,
                    "payment_time": format_date(payment.payment_time) if payment.payment_time else None,
                    "created_at": format_date(payment.created_at)
                })
            
            # 获取计划详情
            plan_data = self.membership_config.get("plans", {}).get(subscription.plan_id, {})
            
            return {
                "status": "success",
                "subscription": self._format_subscription(subscription),
                "plan_details": {
                    "name": plan_data.get("name", subscription.plan_id),
                    "description": plan_data.get("description", ""),
                    "features": plan_data.get("features", []),
                    "essay_limit_daily": plan_data.get("essay_limit_daily", 0),
                    "essay_limit_monthly": plan_data.get("essay_limit_monthly", 0)
                },
                "payments": payment_records
            }
            
        except Exception as e:
            logger.error(f"获取订阅详情时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取订阅详情时发生错误: {str(e)}"
            }
    
    def activate_subscription(self, subscription_id: int) -> Dict[str, Any]:
        """
        激活订阅（支付成功后调用）
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            Dict: 激活结果
        """
        try:
            # 获取订阅
            subscription = db.session.query(Subscription).filter_by(id=subscription_id).first()
            
            if not subscription:
                return {
                    "status": "error",
                    "message": "订阅不存在"
                }
                
            # 检查订阅状态
            if subscription.status == SubscriptionStatus.ACTIVE.value:
                return {
                    "status": "success",
                    "message": "订阅已激活"
                }
                
            if subscription.status != SubscriptionStatus.PENDING.value:
                return {
                    "status": "error",
                    "message": f"订阅状态为{subscription.status}，无法激活"
                }
                
            # 获取用户
            user = db.session.query(User).filter_by(id=subscription.user_id).first()
            if not user:
                return {
                    "status": "error",
                    "message": "用户不存在"
                }
                
            # 获取计划详情
            plan_data = self.membership_config.get("plans", {}).get(subscription.plan_id, {})
            membership_level = plan_data.get("level", "BASIC")
            
            # 计算订阅开始和结束时间
            now = datetime.datetime.now()
            start_date = now
            
            # 如果用户已有有效会员，从到期日开始续费
            if user.membership_expires and user.membership_expires > now:
                start_date = user.membership_expires
            
            # 计算结束时间
            if subscription.duration == "monthly":
                end_date = add_months(start_date, 1)
            elif subscription.duration == "yearly":
                end_date = add_months(start_date, 12)
            else:
                end_date = add_months(start_date, 1)  # 默认一个月
            
            # 更新订阅信息
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.start_date = start_date
            subscription.end_date = end_date
            subscription.updated_at = now
            
            # 更新用户会员信息
            user.membership_level = membership_level
            user.membership_expires = end_date
            
            db.session.commit()
            
            logger.info(f"用户 {user.id} 激活订阅 {subscription_id}，会员等级：{membership_level}，到期时间：{end_date}")
            
            return {
                "status": "success",
                "message": "订阅激活成功",
                "subscription": self._format_subscription(subscription),
                "membership": {
                    "level": membership_level,
                    "expires": format_date(end_date)
                }
            }
            
        except Exception as e:
            logger.error(f"激活订阅时发生错误: {str(e)}", exc_info=True)
            if 'db_session' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"激活订阅时发生错误: {str(e)}"
            }
    
    def process_expired_subscriptions(self) -> Dict[str, Any]:
        """
        处理过期订阅（定时任务调用）
        
        Returns:
            Dict: 处理结果
        """
        try:
            now = datetime.datetime.now()
            
            # 查找已过期订阅
            expired_subscriptions = db.session.query(Subscription).filter(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.end_date < now
            ).all()
            
            processed_count = 0
            renewed_count = 0
            downgraded_count = 0
            
            for subscription in expired_subscriptions:
                # 获取用户
                user = db.session.query(User).filter_by(id=subscription.user_id).first()
                if not user:
                    continue
                
                # 处理已过期订阅
                if subscription.auto_renew:
                    # 自动续费
                    result = self._renew_subscription(subscription)
                    
                    if result.get("status") == "success":
                        renewed_count += 1
                    else:
                        # 续费失败，订阅过期
                        subscription.status = SubscriptionStatus.EXPIRED.value
                        subscription.updated_at = now
                        
                        # 用户降级为免费会员
                        user.membership_level = MembershipLevel.FREE.value
                        user.membership_expires = None
                        
                        downgraded_count += 1
                else:
                    # 非自动续费，直接过期
                    subscription.status = SubscriptionStatus.EXPIRED.value
                    subscription.updated_at = now
                    
                    # 用户降级为免费会员
                    user.membership_level = MembershipLevel.FREE.value
                    user.membership_expires = None
                    
                    downgraded_count += 1
                
                processed_count += 1
            
            db.session.commit()
            
            logger.info(f"处理过期订阅：处理 {processed_count} 个, 续费 {renewed_count} 个, 降级 {downgraded_count} 个")
            
            return {
                "status": "success",
                "message": f"处理过期订阅完成",
                "processed_count": processed_count,
                "renewed_count": renewed_count,
                "downgraded_count": downgraded_count
            }
            
        except Exception as e:
            logger.error(f"处理过期订阅时发生错误: {str(e)}", exc_info=True)
            if 'db_session' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"处理过期订阅时发生错误: {str(e)}"
            }
    
    def _renew_subscription(self, subscription: Subscription) -> Dict[str, Any]:
        """
        续费订阅（内部方法）
        
        Args:
            subscription: 订阅对象
            
        Returns:
            Dict: 续费结果
        """
        try:
            # 创建新的订阅记录
            new_subscription = Subscription(
                user_id=subscription.user_id,
                plan_id=subscription.plan_id,
                price=subscription.price,
                duration=subscription.duration,
                auto_renew=subscription.auto_renew,
                status=SubscriptionStatus.PENDING.value
            )
            
            db.session.add(new_subscription)
            db.session.commit()
            
            # 使用用户默认支付方式支付
            # 实际应用中可能需要存储用户的支付方式偏好
            # 这里简化处理，假设使用上次的支付方式
            last_payment = db.session.query(Payment).filter(
                Payment.subscription_id == subscription.id,
                Payment.status == PaymentStatus.SUCCESS.value
            ).order_by(Payment.created_at.desc()).first()
            
            payment_method = last_payment.payment_method if last_payment else "alipay"
            
            # 创建支付
            result = self.payment_service.create_payment(new_subscription.id, payment_method)
            
            # 如果创建支付成功，模拟支付成功（实际应该由支付回调处理）
            if result.get("status") == "success":
                # 在实际应用中，不应该直接调用激活，而应该由支付回调处理
                # 这里仅作为示例演示
                self.activate_subscription(new_subscription.id)
                
                return {
                    "status": "success",
                    "message": "订阅续费成功",
                    "subscription_id": new_subscription.id
                }
            else:
                return {
                    "status": "error",
                    "message": f"订阅续费失败: {result.get('message')}",
                    "subscription_id": new_subscription.id
                }
            
        except Exception as e:
            logger.error(f"续费订阅时发生错误: {str(e)}", exc_info=True)
            if 'db_session' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"续费订阅时发生错误: {str(e)}"
            }
    
    def _format_subscription(self, subscription: Subscription) -> Dict[str, Any]:
        """
        格式化订阅信息（内部方法）
        
        Args:
            subscription: 订阅对象
            
        Returns:
            Dict: 格式化后的订阅信息
        """
        if not subscription:
            return None
            
        plan_data = self.membership_config.get("plans", {}).get(subscription.plan_id, {})
        
        return {
            "id": subscription.id,
            "plan_id": subscription.plan_id,
            "plan_name": plan_data.get("name", subscription.plan_id),
            "status": subscription.status,
            "price": subscription.price,
            "duration": subscription.duration,
            "start_date": format_date(subscription.start_date) if subscription.start_date else None,
            "end_date": format_date(subscription.end_date) if subscription.end_date else None,
            "auto_renew": subscription.auto_renew,
            "created_at": format_date(subscription.created_at),
            "updated_at": format_date(subscription.updated_at)
        }
    
    def _calculate_discount(self, monthly_price: float, yearly_price: float) -> int:
        """
        计算年付折扣百分比（内部方法）
        
        Args:
            monthly_price: 月付价格
            yearly_price: 年付价格
            
        Returns:
            int: 折扣百分比
        """
        if monthly_price <= 0 or yearly_price <= 0:
            return 0
            
        monthly_total = monthly_price * 12
        saved = monthly_total - yearly_price
        discount = int((saved / monthly_total) * 100)
        
        return max(0, discount)

    def get_subscriptions_with_pagination(self, page: int = 1, per_page: int = 10, search_term: str = "") -> Tuple[List[Subscription], int]:
        """
        分页获取订阅列表
        
        Args:
            page: 页码，从1开始
            per_page: 每页数量
            search_term: 搜索关键词
            
        Returns:
            Tuple: (订阅列表, 总数)
        """
        try:
            # 构建查询
            query = db.session.query(Subscription)
            
            # 如果有搜索条件，添加过滤
            if search_term:
                # 获取符合条件的用户ID
                user_ids = db.session.query(User.id).filter(
                    or_(
                        User.username.ilike(f'%{search_term}%'),
                        User.email.ilike(f'%{search_term}%'),
                        User.name.ilike(f'%{search_term}%')
                    )
                ).all()
                user_ids = [uid[0] for uid in user_ids]
                
                # 查询这些用户的订阅
                query = query.filter(Subscription.user_id.in_(user_ids))
            
            # 获取总数
            total = query.count()
            
            # 排序和分页
            subscriptions = query.order_by(Subscription.created_at.desc())\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()
            
            logger.info(f"分页获取订阅列表成功，页码: {page}, 每页: {per_page}, 总数: {total}")
            
            return subscriptions, total
            
        except Exception as e:
            logger.error(f"分页获取订阅列表失败: {str(e)}", exc_info=True)
            # 返回空列表和0总数
            return [], 0 