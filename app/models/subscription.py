#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
订阅相关数据模型
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship

from app.models.db import db, BaseModel

class SubscriptionStatus(enum.Enum):
    """订阅状态枚举"""
    PENDING = 'pending'  # 待支付
    ACTIVE = 'active'    # 活跃
    EXPIRED = 'expired'  # 已过期
    CANCELED = 'canceled'  # 已取消
    FAILED = 'failed'    # 支付失败

class Subscription(BaseModel):
    """订阅模型"""
    __tablename__ = 'subscriptions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('membership_plans.id'), nullable=False)
    status = Column(String(20), default=SubscriptionStatus.PENDING.value)  # pending, active, expired, canceled
    auto_renew = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=False, default=datetime.now)
    end_date = Column(DateTime, nullable=False)
    next_billing_date = Column(DateTime)
    payment_method = Column(String(50))
    extra_data = Column(JSON)  # 额外的元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship('User', back_populates='subscriptions')
    plan = relationship('MembershipPlan', back_populates='subscriptions')
    payments = relationship('Payment', back_populates='subscription')
    
    def __repr__(self):
        return f'<Subscription {self.id}>'
    
    def to_dict(self):
        """将订阅记录转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'status': self.status,
            'auto_renew': self.auto_renew,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None,
            'payment_method': self.payment_method,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 