#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员服务模块
处理会员订阅、等级权益和使用限制
"""

import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.config import config
from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.db import db
from app.core.user.user_service import UserService

logger = logging.getLogger(__name__)

class MembershipService:
    """会员服务类，处理会员订阅和权益管理"""
    
    def __init__(self):
        """初始化会员服务"""
        self.user_service = UserService()
        
        # 加载会员计划配置
        self.membership_plans = config.MEMBERSHIP_CONFIG
        
        # 定义会员等级对应的权益
        self.membership_benefits = {
            MembershipLevel.FREE.value: {
                'daily_limit': self.membership_plans.get('free', {}).get('daily_limit', 3),
                'monthly_limit': self.membership_plans.get('free', {}).get('monthly_limit', 10),
                'features': self.membership_plans.get('free', {}).get('features', [])
            },
            MembershipLevel.BASIC.value: {
                'daily_limit': self.membership_plans.get('basic', {}).get('daily_limit', 10),
                'monthly_limit': self.membership_plans.get('basic', {}).get('monthly_limit', 50),
                'features': self.membership_plans.get('basic', {}).get('features', [])
            },
            MembershipLevel.PREMIUM.value: {
                'daily_limit': self.membership_plans.get('premium', {}).get('daily_limit', 100),
                'monthly_limit': self.membership_plans.get('premium', {}).get('monthly_limit', 200),
                'features': self.membership_plans.get('premium', {}).get('features', [])
            }
        }
    
    def get_membership_plans(self) -> Dict[str, Any]:
        """
        获取所有可用的会员计划
        
        Returns:
            Dict: 会员计划信息
        """
        return {
            'status': 'success',
            'plans': self.membership_plans
        }
    
    def get_user_membership(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户的会员信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            Dict: 用户会员信息
        """
        try:
            # 获取用户信息
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                return {'status': 'error', 'message': '用户不存在'}
            
            # 获取用户当前有效的订阅
            active_subscription = self._get_active_subscription(user_id)
            
            # 构建会员信息
            membership_info = {
                'level': user.membership_level,
                'level_name': self._get_level_name(user.membership_level),
                'benefits': self.membership_benefits.get(user.membership_level, {}),
                'has_active_subscription': active_subscription is not None,
                'is_free_tier': user.membership_level == MembershipLevel.FREE.value
            }
            
            # 如果有活跃订阅，添加订阅信息
            if active_subscription:
                membership_info.update({
                    'subscription_id': active_subscription.id,
                    'start_date': active_subscription.start_date.isoformat() if active_subscription.start_date else None,
                    'end_date': active_subscription.end_date.isoformat() if active_subscription.end_date else None,
                    'auto_renew': active_subscription.auto_renew,
                    'subscription_status': active_subscription.status
                })
            
            return {
                'status': 'success',
                'membership': membership_info
            }
        
        except Exception as e:
            logger.error(f"获取用户会员信息时发生错误: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'获取用户会员信息时发生错误: {str(e)}'}
    
    def check_user_limits(self, user_id: int, feature: str = None) -> Dict[str, Any]:
        """
        检查用户是否达到使用限制
        
        Args:
            user_id: 用户ID
            feature: 功能名称（可选）
        
        Returns:
            Dict: 检查结果
        """
        try:
            # 获取用户信息
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                return {'status': 'error', 'message': '用户不存在'}
            
            # 获取会员等级对应的权益
            membership_level = user.membership_level
            benefits = self.membership_benefits.get(membership_level, self.membership_benefits[MembershipLevel.FREE.value])
            
            # 如果指定了特定功能，检查用户是否有该功能权限
            if feature:
                has_feature = feature in benefits.get('features', [])
                return {
                    'status': 'success',
                    'has_access': has_feature,
                    'feature': feature,
                    'membership_level': membership_level,
                    'message': '允许使用此功能' if has_feature else '您的会员等级不支持此功能，请升级'
                }
            
            # 获取使用限制
            return {
                'status': 'success',
                'limits': {
                    'daily_limit': benefits.get('daily_limit', 0),
                    'monthly_limit': benefits.get('monthly_limit', 0)
                },
                'features': benefits.get('features', []),
                'membership_level': membership_level
            }
        
        except Exception as e:
            logger.error(f"检查用户限制时发生错误: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'检查用户限制时发生错误: {str(e)}'}
    
    def upgrade_membership(self, user_id: int, plan_id: str, 
                          payment_method: str = None, duration: str = 'monthly') -> Dict[str, Any]:
        """
        升级用户会员等级
        
        Args:
            user_id: 用户ID
            plan_id: 会员计划ID
            payment_method: 支付方式
            duration: 订阅周期（monthly/yearly）
        
        Returns:
            Dict: 升级结果
        """
        try:
            # 验证会员计划是否存在
            if plan_id not in self.membership_plans:
                return {'status': 'error', 'message': '无效的会员计划'}
            
            # 验证订阅周期是否有效
            if duration not in ['monthly', 'yearly']:
                return {'status': 'error', 'message': '无效的订阅周期'}
            
            # 获取用户信息
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                return {'status': 'error', 'message': '用户不存在'}
            
            # 检查当前会员等级
            if plan_id == 'basic' and user.membership_level == MembershipLevel.PREMIUM.value:
                return {'status': 'error', 'message': '无法从高级会员降级为基础会员，请等待当前订阅到期'}
            
            # 计算订阅开始和结束日期
            start_date = datetime.datetime.now()
            if duration == 'monthly':
                end_date = start_date + datetime.timedelta(days=30)
            else:  # yearly
                end_date = start_date + datetime.timedelta(days=365)
            
            # 计算价格
            price = self.membership_plans.get(plan_id, {}).get('price', 0)
            if duration == 'yearly':
                # 年付通常有折扣
                price = price * 12 * 0.8  # 80%的年付价格作为示例
            
            # 创建订阅记录
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status=SubscriptionStatus.PENDING.value,
                start_date=start_date,
                end_date=end_date,
                price=price,
                duration=duration,
                payment_method=payment_method,
                auto_renew=True  # 默认开启自动续费
            )
            
            # 保存订阅记录
            db.session.add(subscription)
            
            # 更新用户会员等级
            membership_level = MembershipLevel.BASIC.value if plan_id == 'basic' else MembershipLevel.PREMIUM.value
            user.membership_level = membership_level
            
            db.session.commit()
            
            # 返回结果
            return {
                'status': 'success',
                'message': f'已成功升级为{self._get_level_name(membership_level)}',
                'subscription_id': subscription.id,
                'payment_required': True,
                'amount': price,
                'currency': 'CNY',
                'subscription': {
                    'id': subscription.id,
                    'plan_id': plan_id,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'status': subscription.status,
                    'auto_renew': subscription.auto_renew
                }
            }
        
        except Exception as e:
            logger.error(f"升级会员时发生错误: {str(e)}", exc_info=True)
            if 'db.session' in locals() or 'db' in locals():
                db.session.rollback()
            return {'status': 'error', 'message': f'升级会员时发生错误: {str(e)}'}
    
    def cancel_subscription(self, user_id: int, subscription_id: int) -> Dict[str, Any]:
        """
        取消订阅自动续费
        
        Args:
            user_id: 用户ID
            subscription_id: 订阅ID
        
        Returns:
            Dict: 取消结果
        """
        try:
            # 查询订阅记录
            subscription = db.session.query(Subscription).filter(
                Subscription.id == subscription_id,
                Subscription.user_id == user_id
            ).first()
            
            if not subscription:
                return {'status': 'error', 'message': '未找到订阅记录'}
                
            # 检查订阅状态
            if subscription.status != SubscriptionStatus.ACTIVE.value:
                return {'status': 'error', 'message': '只有活跃的订阅才能取消自动续费'}
            
            # 更新自动续费状态
            subscription.auto_renew = False
            subscription.updated_at = datetime.datetime.now()
            
            db.session.commit()
            
            return {'status': 'success', 'message': '已成功取消订阅自动续费'}
        
        except Exception as e:
            logger.error(f"取消订阅时发生错误: {str(e)}", exc_info=True)
            if 'db.session' in locals() or 'db' in locals():
                db.session.rollback()
            return {'status': 'error', 'message': f'取消订阅时发生错误: {str(e)}'}
    
    def renew_subscription(self, subscription_id: int) -> Dict[str, Any]:
        """
        续费订阅（由系统调用）
        
        Args:
            subscription_id: 订阅ID
        
        Returns:
            Dict: 续费结果
        """
        try:
            # 获取订阅信息
            subscription = Subscription.query.get(subscription_id)
            
            if not subscription:
                return {'status': 'error', 'message': '订阅不存在'}
            
            # 检查订阅状态
            if subscription.status != SubscriptionStatus.ACTIVE.value:
                return {'status': 'error', 'message': f'订阅状态为{subscription.status}，无法续费'}
            
            # 检查是否开启自动续费
            if not subscription.auto_renew:
                return {'status': 'error', 'message': '未开启自动续费'}
            
            # 计算新的结束日期
            current_end_date = subscription.end_date
            if subscription.duration == 'monthly':
                new_end_date = current_end_date + datetime.timedelta(days=30)
            else:  # yearly
                new_end_date = current_end_date + datetime.timedelta(days=365)
            
            # 更新订阅记录
            subscription.start_date = current_end_date
            subscription.end_date = new_end_date
            subscription.updated_at = datetime.datetime.now()
            
            db.session.commit()
            
            return {
                'status': 'success',
                'message': '订阅已续费',
                'subscription': {
                    'id': subscription.id,
                    'plan_id': subscription.plan_id,
                    'start_date': subscription.start_date.isoformat() if subscription.start_date else None,
                    'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
                    'auto_renew': subscription.auto_renew
                }
            }
        
        except Exception as e:
            logger.error(f"续费订阅时发生错误: {str(e)}", exc_info=True)
            if 'db.session' in locals() or 'db' in locals():
                db.session.rollback()
            return {'status': 'error', 'message': f'续费订阅时发生错误: {str(e)}'}
    
    def process_expired_subscriptions(self) -> Dict[str, Any]:
        """
        处理已过期的订阅（由定时任务调用）
        
        Returns:
            Dict: 处理结果
        """
        try:
            # 获取当前日期
            now = datetime.datetime.now()
            
            # 查询已过期但状态仍为活跃的订阅
            expired_subscriptions = Subscription.query.filter(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.end_date < now
            ).all()
            
            if not expired_subscriptions:
                logger.info("没有发现过期的订阅")
                return {
                    'status': 'success',
                    'message': '没有发现过期的订阅',
                    'count': 0
                }
            
            processed_count = 0
            auto_renewed_count = 0
            
            for subscription in expired_subscriptions:
                # 检查是否自动续费
                if subscription.auto_renew:
                    # TODO: 调用支付服务处理自动续费
                    # 暂时模拟续费成功
                    renew_result = self.renew_subscription(subscription.id)
                    
                    if renew_result.get('status') == 'success':
                        auto_renewed_count += 1
                    else:
                        # 续费失败，更新订阅状态为过期
                        subscription.status = SubscriptionStatus.EXPIRED.value
                        
                        # 更新用户会员等级为免费
                        user = self.user_service.get_user_by_id(subscription.user_id)
                        if user:
                            user.membership_level = MembershipLevel.FREE.value
                        
                        processed_count += 1
                else:
                    # 未开启自动续费，直接将状态修改为过期
                    subscription.status = SubscriptionStatus.EXPIRED.value
                    
                    # 更新用户会员等级为免费
                    user = self.user_service.get_user_by_id(subscription.user_id)
                    if user:
                        user.membership_level = MembershipLevel.FREE.value
                    
                    processed_count += 1
            
            db.session.commit()
            
            return {
                'status': 'success',
                'message': f'已处理{processed_count}个过期订阅，自动续费{auto_renewed_count}个',
                'processed_count': processed_count,
                'auto_renewed_count': auto_renewed_count,
                'total_count': len(expired_subscriptions)
            }
        
        except Exception as e:
            logger.error(f"处理过期订阅时发生错误: {str(e)}", exc_info=True)
            if 'db.session' in locals() or 'db' in locals():
                db.session.rollback()
            return {'status': 'error', 'message': f'处理过期订阅时发生错误: {str(e)}'}
    
    def _get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """
        获取用户当前有效的订阅
        
        Args:
            user_id: 用户ID
        
        Returns:
            Optional[Subscription]: 活跃订阅或None
        """
        return Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.end_date > datetime.datetime.now()
        ).order_by(Subscription.end_date.desc()).first()
    
    def _get_level_name(self, level: str) -> str:
        """
        获取会员等级的显示名称
        
        Args:
            level: 会员等级ID
        
        Returns:
            str: 会员等级名称
        """
        level_names = {
            MembershipLevel.FREE.value: '免费用户',
            MembershipLevel.BASIC.value: '基础会员',
            MembershipLevel.PREMIUM.value: '高级会员'
        }
        return level_names.get(level, '未知等级') 