#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户相关数据模型
定义用户、角色和权限
"""

from datetime import datetime, timezone, UTC
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Float, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.models.db import db, BaseModel

class MembershipLevel(enum.Enum):
    """会员等级枚举"""
    FREE = 'free'        # 免费用户
    BASIC = 'basic'      # 基础会员
    PREMIUM = 'premium'  # 高级会员

class Permission(BaseModel):
    """权限模型"""
    __tablename__ = 'permissions'
    
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(200))
    
    # 关系
    role_permissions = relationship('RolePermission', back_populates='permission')
    
    def __repr__(self):
        return f'<Permission {self.name}>'
    
    @staticmethod
    def create_default_permissions():
        """创建默认权限"""
        default_permissions = [
            ('all', '所有权限'),
            ('manage_essays', '管理作文'),
            ('view_reports', '查看报告'),
            ('manage_own_essays', '管理自己的作文'),
            ('view_own_reports', '查看自己的报告'),
            ('manage_users', '管理用户'),
            ('manage_own_students', '管理自己的学生'),
            ('view_public_content', '查看公开内容'),
            ('manage_system', '管理系统'),
            ('manage_roles', '管理角色'),
            ('manage_permissions', '管理权限')
        ]
        
        for name, description in default_permissions:
            permission = Permission.query.filter_by(name=name).first()
            if not permission:
                permission = Permission(name=name, description=description)
                db.session.add(permission)
        
        db.session.commit()

class Role(BaseModel):
    """角色模型"""
    __tablename__ = 'roles'
    
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(200))
    
    # 关系
    user_roles = relationship('UserRole', back_populates='role')
    role_permissions = relationship('RolePermission', back_populates='role')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def add_permission(self, permission):
        """添加权限"""
        if not self.has_permission(permission.name):
            role_perm = RolePermission(role=self, permission=permission)
            db.session.add(role_perm)
    
    def remove_permission(self, permission):
        """移除权限"""
        role_perm = RolePermission.query.filter_by(role=self, permission=permission).first()
        if role_perm:
            db.session.delete(role_perm)
    
    def has_permission(self, permission_name):
        """检查角色是否拥有指定权限"""
        return any(rp.permission.name == permission_name for rp in self.role_permissions)
    
    @staticmethod
    def create_default_roles():
        """创建默认角色"""
        roles = {
            'admin': ['all'],
            'teacher': ['manage_essays', 'view_reports', 'manage_own_students'],
            'student': ['manage_own_essays', 'view_own_reports'],
            'guest': ['view_public_content']
        }
        
        for role_name, permissions in roles.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name, description=f'{role_name} role')
                db.session.add(role)
            
            for perm_name in permissions:
                perm = Permission.query.filter_by(name=perm_name).first()
                if perm:
                    role_perm = RolePermission(role=role, permission=perm)
                    db.session.add(role_perm)
        
        db.session.commit()

class User(BaseModel, UserMixin):
    """用户模型"""
    __tablename__ = 'users'
    
    # 基本信息
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(200), nullable=False)
    
    # 用户状态
    _is_active = Column(Boolean, default=True)  # 统一使用_is_active
    _is_admin = Column('is_admin', Boolean, default=False)  # 重命名列名为is_admin
    is_verified = Column(Boolean, default=False)  # 邮箱验证
    is_deleted = Column(Boolean, default=False)  # 软删除标记
    
    # 个人资料
    name = Column(String(100))
    avatar = Column(String(200))
    bio = Column(String(200))
    
    # 最后登录信息
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(50))
    
    # 会员信息
    membership_level = Column(String(20), default=MembershipLevel.FREE.value)
    membership_expires = Column(DateTime)
    
    # 统计
    essay_count = Column(Integer, default=0)
    
    # 注册和登录信息
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # 一对多关系：用户拥有多个作文
    essays = relationship('Essay', back_populates='user', lazy='dynamic',
                         cascade='all, delete-orphan')
    
    # 一对一关系：用户资料
    profile = relationship('UserProfile', uselist=False, 
                          back_populates='user', cascade='all, delete-orphan')
    
    # 一对多关系：用户支付记录
    payments = relationship('Payment', back_populates='user', lazy='dynamic')
    
    # 用户角色关系
    user_roles = relationship('UserRole', back_populates='user')
    
    # 用户订阅关系
    subscriptions = relationship('Subscription', back_populates='user')
    
    # 用户会员关系
    membership = relationship('Membership', back_populates='user', uselist=False)
    
    # 验证码关系
    verification_codes = relationship('VerificationCode', back_populates='user')
    
    # 反馈关系
    feedbacks = relationship('UserFeedback', back_populates='user')
    
    # 批改关系
    corrections = relationship('Correction', back_populates='corrector')
    
    @property
    def roles(self):
        """兼容性属性：返回角色列表，解决'User' object has no attribute 'roles'错误"""
        if hasattr(self, 'user_roles') and self.user_roles:
            return [ur.role for ur in self.user_roles]
        return []
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """设置密码"""
        if not password:
            raise ValueError("密码不能为空")
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """检查密码是否正确"""
        if not password or not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        """检查用户是否拥有指定角色"""
        return any(ur.role.name == role_name for ur in self.user_roles)
    
    def has_permission(self, permission_name):
        """检查用户是否拥有指定权限"""
        # 管理员拥有所有权限
        if self.is_admin:
            return True
            
        # 检查角色权限
        for user_role in self.user_roles:
            if user_role.role.has_permission(permission_name):
                return True
                
        return False
    
    def get_id(self):
        """获取用户ID"""
        return str(self.id)
    
    @property
    def active(self):
        """兼容性属性，返回_is_active值"""
        return self._is_active
    
    @active.setter
    def active(self, value):
        """兼容性setter，设置_is_active值"""
        self._is_active = value
    
    @property
    def is_admin(self):
        """获取管理员状态"""
        return self._is_admin

    @is_admin.setter
    def is_admin(self, value):
        """设置管理员状态"""
        self._is_admin = value
    
    @property
    def is_authenticated(self):
        """判断用户是否已认证"""
        return True
    
    @property
    def is_active(self):
        """判断用户是否激活"""
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        """设置用户激活状态"""
        self._is_active = value
    
    @property
    def is_anonymous(self):
        """判断是否是匿名用户"""
        return False
    
    def get_remaining_corrections(self):
        """获取用户剩余的批改次数"""
        if not self.profile:
            return 0
            
        if self.profile.is_subscription_active():
            return float('inf')  # 订阅用户无限制
            
        return max(0, self.profile.essay_monthly_limit - self.profile.essay_monthly_used)
        
    def get_daily_remaining_corrections(self):
        """获取用户每日剩余的批改次数"""
        if not self.profile:
            return 0
            
        if self.profile.is_subscription_active():
            return float('inf')  # 订阅用户无限制
            
        # 获取用户的限制配置
        if hasattr(self.profile, 'get_essay_limits'):
            limits = self.profile.get_essay_limits()
            return max(0, limits.get('daily', 1))  # 默认每日限制为1
        else:
            return 1  # 默认每日限制为1

class UserRole(BaseModel):
    """用户-角色关联模型"""
    __tablename__ = 'user_roles'
    
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    # 关系
    user = relationship('User', back_populates='user_roles')
    role = relationship('Role', back_populates='user_roles')

class RolePermission(BaseModel):
    """角色-权限关联模型"""
    __tablename__ = 'role_permissions'
    
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    # 关系
    role = relationship('Role', back_populates='role_permissions')
    permission = relationship('Permission', back_populates='role_permissions')

class UserProfile(BaseModel):
    """用户资料模型"""
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    # 基本信息
    nickname = Column(String(50))
    avatar_url = Column(String(255))
    gender = Column(String(10))
    birth_date = Column(DateTime)
    
    # 教育信息
    school = Column(String(100))
    grade = Column(String(50))
    
    # 联系信息
    phone = Column(String(20))
    address = Column(String(255))
    
    # 隐私设置
    privacy_settings = Column(String(1000))  # JSON格式的隐私设置
    
    # 订阅信息
    subscription_status = Column(String(20), default='free')
    subscription_plan_id = Column(Integer, ForeignKey('membership_plans.id'), nullable=True)
    subscription_expires = Column(DateTime, nullable=True)
    
    # 文章使用限制
    essay_monthly_limit = Column(Integer, default=3)
    essay_monthly_used = Column(Integer, default=0)
    reset_date = Column(DateTime, default=datetime.now(UTC))
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # 关系
    user = relationship('User', back_populates='profile')
    subscription_plan = relationship('MembershipPlan', foreign_keys=[subscription_plan_id])
    
    monthly_limit = Column(Integer, default=0)  # 月度批改限制
    monthly_used = Column(Integer, default=0)   # 已使用的批改次数
    
    def is_subscription_active(self):
        """检查用户是否有活跃订阅"""
        if self.subscription_status != 'active':
            return False
            
        if not self.subscription_expires:
            return False
            
        return self.subscription_expires > datetime.now(UTC)
    
    def get_essay_limits(self):
        """获取用户的作文限制配置"""
        if self.is_subscription_active() and self.subscription_plan:
            return {
                'daily': self.subscription_plan.max_essays_per_day if hasattr(self.subscription_plan, 'max_essays_per_day') else 999,
                'monthly': self.subscription_plan.max_essays_total if hasattr(self.subscription_plan, 'max_essays_total') else 999
            }
        else:
            # 免费用户限制
            return {
                'daily': 1,
                'monthly': self.essay_monthly_limit
            }
    
    def has_essay_remaining(self):
        """检查用户是否在每月配额中还有剩余文章"""
        # 如果订阅活跃则始终允许
        if self.is_subscription_active():
            return True
            
        # 检查每月限制
        return self.essay_monthly_used < self.essay_monthly_limit
        
    def update_essay_limits(self, daily_limit, monthly_limit):
        """更新用户的批改次数限制"""
        try:
            # 更新每月限制
            self.essay_monthly_limit = monthly_limit
            
            # 如果存在订阅计划，更新订阅计划的限制
            if self.subscription_plan:
                if hasattr(self.subscription_plan, 'max_essays_per_day'):
                    self.subscription_plan.max_essays_per_day = daily_limit
                if hasattr(self.subscription_plan, 'max_essays_total'):
                    self.subscription_plan.max_essays_total = monthly_limit
                
            return True
        except Exception as e:
            import logging
            logging.error(f"更新用户批改次数限制失败: {str(e)}")
            return False
            
    def __repr__(self):
        return f'<UserProfile {self.user_id}>'

class VerificationCode(BaseModel):
    """验证码模型"""
    __tablename__ = 'verification_codes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    code = Column(String(10), nullable=False)
    purpose = Column(String(20), nullable=False)  # registration, password_reset, login
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    # 关联到用户
    user = relationship('User', back_populates='verification_codes')
    
    def __repr__(self):
        return f'<VerificationCode(id={self.id}, user_id={self.user_id}, purpose={self.purpose})>' 