#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员和订阅相关数据模型
"""

from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship

from app.models.db import db, BaseModel

class MembershipLevel(enum.Enum):
    """会员等级枚举"""
    BASIC = 'basic'
    PREMIUM = 'premium'
    PROFESSIONAL = 'professional'

class MembershipPlan(BaseModel):
    """会员计划模型"""
    __tablename__ = 'membership_plans'
    
    # 基本信息
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    
    # 价格信息
    price = Column(Float, nullable=False)
    currency = Column(String(10), default='CNY')
    duration_days = Column(Integer, nullable=False)  # 会员持续天数
    
    # 会员权益
    max_essays_per_day = Column(Integer, default=3)
    max_essays_total = Column(Integer, default=100)
    features = Column(JSON)  # 特性列表
    
    # 状态
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    # 关联的会员
    memberships = relationship('Membership', back_populates='plan')
    subscriptions = relationship('Subscription', back_populates='plan')
    
    def __repr__(self):
        return f'<MembershipPlan {self.name}>'
    
    @staticmethod
    def create_default_plans():
        """创建默认会员计划"""
        default_plans = [
            {
                'name': '基础会员',
                'code': 'basic',
                'description': '基础会员权益，每日最多批改3篇作文',
                'price': 49.0,
                'duration_days': 30,
                'max_essays_per_day': 3,
                'max_essays_total': 100,
                'features': ['基础批改', '语法检查', '标准评分'],
                'display_order': 1,
            },
            {
                'name': '高级会员',
                'code': 'premium',
                'description': '高级会员权益，每日最多批改10篇作文，包含高级分析',
                'price': 99.0,
                'duration_days': 30,
                'max_essays_per_day': 10,
                'max_essays_total': 300,
                'features': ['高级批改', '语法检查', '详细评分', '内容建议', '结构分析'],
                'display_order': 2,
            },
            {
                'name': '专业会员',
                'code': 'professional',
                'description': '专业会员权益，无限批改，包含所有高级功能',
                'price': 199.0,
                'duration_days': 30,
                'max_essays_per_day': 0,  # 无限制
                'max_essays_total': 0,    # 无限制
                'features': ['专业批改', '语法检查', '详细评分', '内容建议', '结构分析', '个性化指导', '优先处理'],
                'display_order': 3,
            }
        ]
        
        for plan_data in default_plans:
            plan = MembershipPlan.query.filter_by(code=plan_data['code']).first()
            if not plan:
                plan = MembershipPlan(**plan_data)
                db.session.add(plan)
        
        db.session.commit()

class Membership(BaseModel):
    """用户会员模型"""
    __tablename__ = 'memberships'
    
    # 用户ID
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    # 会员计划
    plan_id = Column(Integer, ForeignKey('membership_plans.id'), nullable=False)
    
    # 会员期限
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    
    # 会员状态
    is_active = Column(Boolean, default=True)
    is_auto_renew = Column(Boolean, default=False)
    
    # 使用统计
    essays_used_today = Column(Integer, default=0)
    essays_used_total = Column(Integer, default=0)
    last_essay_date = Column(DateTime)
    
    # 关系
    user = relationship('User', back_populates='membership')
    plan = relationship('MembershipPlan', back_populates='memberships')
    
    def __repr__(self):
        return f'<Membership user_id={self.user_id} plan={self.plan.name if self.plan else None}>'
    
    def is_expired(self):
        """检查会员是否已过期"""
        return datetime.utcnow() > self.end_date
    
    def reset_daily_usage(self):
        """重置每日使用量"""
        today = datetime.utcnow().date()
        if self.last_essay_date != today:
            self.essays_used_today = 0
            self.last_essay_date = today
            db.session.commit()
    
    def get_remaining_info(self):
        """获取会员剩余次数信息"""
        # 确保每日使用量是最新的
        self.reset_daily_usage()
        
        user_type = 'free'  # 默认为免费用户
        if self.plan and hasattr(self.plan, 'code'):
            if self.plan.code.lower() == 'premium':
                user_type = 'premium'
            elif self.plan.code.lower() == 'regular' or self.plan.code.lower() == 'basic':
                user_type = 'regular'
        
        # 计算剩余次数
        max_essays_per_day = self.plan.max_essays_per_day if self.plan else 3
        max_essays_total = self.plan.max_essays_total if self.plan else 10
        
        daily_remaining = max(0, max_essays_per_day - self.essays_used_today)
        total_remaining = max(0, max_essays_total - self.essays_used_total)
        
        return {
            'user_type': user_type,
            'daily_remaining': daily_remaining,
            'total_remaining': total_remaining
        }
    
    def can_submit_essay(self):
        """检查用户是否可以提交作文"""
        if not self.is_active or self.is_expired():
            return False
        
        self.reset_daily_usage()
        
        # 检查每日限制
        if self.plan.max_essays_per_day > 0 and self.essays_used_today >= self.plan.max_essays_per_day:
            return False
        
        # 检查总数限制
        if self.plan.max_essays_total > 0 and self.essays_used_total >= self.plan.max_essays_total:
            return False
        
        return True
    
    def increment_usage(self):
        """增加使用次数"""
        self.reset_daily_usage()
        self.essays_used_today += 1
        self.essays_used_total += 1
        db.session.commit()

class Coupon(BaseModel):
    """优惠券模型"""
    __tablename__ = 'coupons'
    
    # 优惠券信息
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # 优惠类型
    discount_type = Column(String(20), nullable=False)  # percentage, fixed
    discount_value = Column(Float, nullable=False)
    
    # 适用范围
    applicable_plans = Column(JSON)  # 适用的会员计划ID列表
    
    # 限制条件
    min_order_amount = Column(Float, default=0)
    max_discount_amount = Column(Float)
    
    # 有效期
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime)
    
    # 使用限制
    max_uses = Column(Integer)
    max_uses_per_user = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    
    # 状态
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f'<Coupon {self.code}>'
    
    def is_valid(self):
        """检查优惠券是否有效"""
        now = datetime.utcnow()
        
        # 检查是否激活
        if not self.is_active:
            return False
        
        # 检查时间有效期
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        
        # 检查使用次数限制
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        
        return True
    
    def calculate_discount(self, order_amount, plan_id=None):
        """计算折扣金额"""
        if not self.is_valid():
            return 0
        
        # 检查最低订单金额
        if order_amount < self.min_order_amount:
            return 0
        
        # 检查适用的会员计划
        if self.applicable_plans and plan_id is not None:
            if str(plan_id) not in self.applicable_plans:
                return 0
        
        # 计算折扣金额
        if self.discount_type == 'percentage':
            discount = order_amount * (self.discount_value / 100)
        else:  # fixed
            discount = self.discount_value
        
        # 确保不超过最大折扣金额
        if self.max_discount_amount and discount > self.max_discount_amount:
            discount = self.max_discount_amount
        
        # 确保不超过订单金额
        if discount > order_amount:
            discount = order_amount
        
        return discount 