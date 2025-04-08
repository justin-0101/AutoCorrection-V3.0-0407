#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员订阅服务模块
处理订阅生命周期和支付集成
"""

import logging
from datetime import datetime, timedelta
import json
import uuid

from app.models.db import db
from app.models.user import User, UserProfile
from app.models.subscription import Subscription
from app.utils.exceptions import PaymentError, ValidationError, ResourceNotFoundError
from app.utils.websocket_manager import notify_user

# 获取logger
logger = logging.getLogger(__name__)

class SubscriptionService:
    """订阅服务"""
    
    def __init__(self):
        """初始化订阅服务"""
        # 从配置获取支付设置
        from app.config import PAYMENT_CONFIG, MEMBERSHIP_CONFIG
        self.payment_config = PAYMENT_CONFIG
        self.membership_config = MEMBERSHIP_CONFIG
    
    def get_plan_details(self, plan_id):
        """
        获取套餐详情
        
        Args:
            plan_id: 套餐ID
            
        Returns:
            dict: 套餐详情
        """
        plans = self.membership_config.get('plans', [])
        
        for plan in plans:
            if plan.get('id') == plan_id:
                return {
                    "status": "success",
                    "data": plan
                }
        
        logger.warning(f"找不到套餐详情: {plan_id}")
        return {
            "status": "error",
            "message": f"找不到套餐详情: {plan_id}"
        }
    
    def create_subscription_order(self, user_id, plan_id, payment_method="alipay"):
        """
        创建订阅订单
        
        Args:
            user_id: 用户ID
            plan_id: 套餐ID
            payment_method: 支付方式
            
        Returns:
            dict: 订单信息和支付链接
        """
        try:
            # 检查用户是否存在
            with db.session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    raise ResourceNotFoundError(f"用户不存在: {user_id}")
            
            # 获取套餐详情
            plan_details = self.get_plan_details(plan_id)
            if plan_details.get("status") != "success":
                return plan_details
            
            plan = plan_details.get("data", {})
            
            # 生成订单号
            order_id = f"SUB_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # 在实际系统中，这里会调用支付网关API创建支付订单
            # 这里模拟支付流程
            from app.services.payment_service import PaymentService
            payment_service = PaymentService()
            
            payment_result = payment_service.create_payment_order(
                user_id=user_id,
                order_id=order_id,
                amount=plan.get('price', 0),
                payment_method=payment_method,
                description=f"订阅{plan.get('name', '会员套餐')}"
            )
            
            if payment_result.get("status") != "success":
                return payment_result
            
            payment_data = payment_result.get("data", {})
            
            # 记录订阅订单
            # 注意: 此时订阅尚未生效，将在支付完成后激活
            with db.session() as session:
                new_subscription = Subscription(
                    user_id=user_id,
                    plan=plan_id,
                    start_date=None,  # 支付完成后设置
                    end_date=None,  # 支付完成后设置
                    is_active=False,
                    payment_id=payment_data.get("payment_id")
                )
                
                session.add(new_subscription)
                session.commit()
                
                logger.info(f"创建订阅订单成功，用户ID: {user_id}, 订单ID: {order_id}, 订阅ID: {new_subscription.id}")
            
            return {
                "status": "success",
                "data": {
                    "order_id": order_id,
                    "subscription_id": new_subscription.id,
                    "payment_url": payment_data.get("payment_url"),
                    "payment_id": payment_data.get("payment_id"),
                    "plan": plan,
                    "expires_in": 1800  # 订单有效期30分钟
                }
            }
        
        except ResourceNotFoundError as e:
            logger.error(f"创建订阅订单失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"创建订阅订单失败: {str(e)}")
            return {
                "status": "error",
                "message": f"创建订阅订单失败: {str(e)}"
            }
    
    def process_payment_callback(self, payment_id, payment_status, transaction_data):
        """
        处理支付回调
        
        Args:
            payment_id: 支付ID
            payment_status: 支付状态
            transaction_data: 交易数据
            
        Returns:
            dict: 处理结果
        """
        try:
            logger.info(f"处理支付回调，支付ID: {payment_id}, 状态: {payment_status}")
            
            # 检查支付状态
            if payment_status != "success":
                logger.warning(f"支付未成功，状态: {payment_status}")
                return {
                    "status": "error",
                    "message": "支付未成功"
                }
            
            # 查找对应的订阅
            with db.session() as session:
                subscription = session.query(Subscription).filter_by(payment_id=payment_id).first()
                
                if not subscription:
                    logger.error(f"找不到对应的订阅，支付ID: {payment_id}")
                    return {
                        "status": "error",
                        "message": "找不到对应的订阅"
                    }
                
                # 检查用户
                user = session.query(User).filter_by(id=subscription.user_id).first()
                if not user:
                    logger.error(f"找不到对应的用户，用户ID: {subscription.user_id}")
                    return {
                        "status": "error",
                        "message": "找不到对应的用户"
                    }
                
                # 异步处理订阅
                from app.tasks.subscription_tasks import process_subscription_task
                task = process_subscription_task.delay(
                    user_id=user.id,
                    payment_id=payment_id,
                    plan_id=subscription.plan,
                    amount=transaction_data.get("amount", 0)
                )
                
                logger.info(f"启动异步订阅处理任务，任务ID: {task.id}")
                
                return {
                    "status": "success",
                    "message": "支付回调处理成功，开始更新订阅",
                    "task_id": task.id
                }
                
        except Exception as e:
            logger.error(f"处理支付回调失败: {str(e)}")
            return {
                "status": "error",
                "message": f"处理支付回调失败: {str(e)}"
            }
    
    def activate_subscription(self, user_id, subscription_id, payment_id):
        """
        激活订阅
        
        Args:
            user_id: 用户ID
            subscription_id: 订阅ID
            payment_id: 支付ID
            
        Returns:
            dict: 激活结果
        """
        try:
            with db.session() as session:
                subscription = session.query(Subscription).filter_by(
                    id=subscription_id,
                    user_id=user_id,
                    payment_id=payment_id
                ).first()
                
                if not subscription:
                    raise ResourceNotFoundError(f"找不到对应的订阅: {subscription_id}")
                
                # 获取套餐详情
                plan_details = self.get_plan_details(subscription.plan)
                if plan_details.get("status") != "success":
                    return plan_details
                
                plan = plan_details.get("data", {})
                duration_days = plan.get("duration_days", 30)
                essay_limit = plan.get("essay_limit", 10)
                
                # 设置订阅开始和结束时间
                now = datetime.now()
                subscription.start_date = now
                subscription.end_date = now + timedelta(days=duration_days)
                subscription.is_active = True
                
                # 更新用户资料
                profile = session.query(UserProfile).filter_by(user_id=user_id).first()
                
                if profile:
                    # 检查是否有现有的有效订阅
                    if profile.subscription_expires and profile.subscription_expires > now:
                        # 延长现有订阅
                        profile.subscription_expires += timedelta(days=duration_days)
                    else:
                        # 新订阅
                        profile.subscription_expires = now + timedelta(days=duration_days)
                    
                    # 更新配额
                    profile.essay_monthly_limit = essay_limit
                else:
                    # 创建新的用户资料
                    profile = UserProfile(
                        user_id=user_id,
                        subscription_expires=now + timedelta(days=duration_days),
                        essay_monthly_limit=essay_limit,
                        essay_monthly_used=0,
                        reset_date=now
                    )
                    session.add(profile)
                
                session.commit()
                
                # 发送通知
                notify_user(user_id, {
                    "type": "subscription_activated",
                    "subscription": {
                        "plan": subscription.plan,
                        "start_date": subscription.start_date.isoformat(),
                        "end_date": subscription.end_date.isoformat(),
                        "essay_limit": essay_limit
                    }
                })
                
                logger.info(f"订阅激活成功，用户ID: {user_id}, 订阅ID: {subscription_id}")
                
                return {
                    "status": "success",
                    "data": {
                        "subscription_id": subscription.id,
                        "start_date": subscription.start_date.isoformat(),
                        "end_date": subscription.end_date.isoformat(),
                        "essay_limit": essay_limit,
                        "plan": subscription.plan
                    }
                }
                
        except ResourceNotFoundError as e:
            logger.error(f"激活订阅失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"激活订阅失败: {str(e)}")
            return {
                "status": "error",
                "message": f"激活订阅失败: {str(e)}"
            }
    
    def cancel_subscription(self, user_id, subscription_id):
        """
        取消订阅
        
        Args:
            user_id: 用户ID
            subscription_id: 订阅ID
            
        Returns:
            dict: 取消结果
        """
        try:
            with db.session() as session:
                subscription = session.query(Subscription).filter_by(
                    id=subscription_id,
                    user_id=user_id,
                    is_active=True
                ).first()
                
                if not subscription:
                    raise ResourceNotFoundError(f"找不到有效的订阅: {subscription_id}")
                
                # 更新订阅状态
                subscription.is_active = False
                
                session.commit()
                
                # 发送通知
                notify_user(user_id, {
                    "type": "subscription_cancelled",
                    "subscription": {
                        "subscription_id": subscription_id,
                        "end_date": subscription.end_date.isoformat()
                    }
                })
                
                logger.info(f"取消订阅成功，用户ID: {user_id}, 订阅ID: {subscription_id}")
                
                return {
                    "status": "success",
                    "message": "订阅已取消，您可以继续使用服务至订阅结束日期",
                    "data": {
                        "subscription_id": subscription.id,
                        "end_date": subscription.end_date.isoformat()
                    }
                }
                
        except ResourceNotFoundError as e:
            logger.error(f"取消订阅失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"取消订阅失败: {str(e)}")
            return {
                "status": "error",
                "message": f"取消订阅失败: {str(e)}"
            }
    
    def get_user_subscriptions(self, user_id):
        """
        获取用户的订阅历史
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 订阅历史
        """
        try:
            with db.session() as session:
                subscriptions = session.query(Subscription)\
                    .filter_by(user_id=user_id)\
                    .order_by(Subscription.start_date.desc())\
                    .all()
                
                result = []
                
                for sub in subscriptions:
                    # 获取套餐信息
                    plan_details = self.get_plan_details(sub.plan)
                    plan_name = plan_details.get("data", {}).get("name", "未知套餐")
                    
                    result.append({
                        "id": sub.id,
                        "plan": sub.plan,
                        "plan_name": plan_name,
                        "start_date": sub.start_date.isoformat() if sub.start_date else None,
                        "end_date": sub.end_date.isoformat() if sub.end_date else None,
                        "is_active": sub.is_active,
                        "payment_id": sub.payment_id
                    })
                
                logger.info(f"获取用户订阅历史成功，用户ID: {user_id}, 共{len(result)}条记录")
                
                return {
                    "status": "success",
                    "data": result
                }
                
        except Exception as e:
            logger.error(f"获取用户订阅历史失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取用户订阅历史失败: {str(e)}"
            } 