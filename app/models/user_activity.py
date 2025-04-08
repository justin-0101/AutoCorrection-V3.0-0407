#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户活动相关数据模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.models.db import db, BaseModel

class UserActivity(BaseModel):
    """用户活动记录模型"""
    __tablename__ = 'user_activities'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String(50))  # login, logout, profile_update, etc.
    ip_address = Column(String(50))  # IP地址
    user_agent = Column(String(200))  # 用户代理
    description = Column(Text)  # 活动描述
    extra_data = Column(JSON)  # 额外的元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship('User', backref='activities')
    
    def __repr__(self):
        return f'<UserActivity {self.id}>'
    
    def to_dict(self):
        """将活动记录转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'description': self.description,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def log_activity(cls, user_id, activity_type, description=None, 
                    ip_address=None, user_agent=None, context_data=None):
        """
        记录一个用户活动
        
        Args:
            user_id: 用户ID
            activity_type: 活动类型
            description: 活动描述
            ip_address: IP地址
            user_agent: 用户代理
            context_data: 上下文数据，JSON格式
            
        Returns:
            UserActivity: 创建的活动记录
        """
        activity = cls(
            user_id=user_id,
            type=activity_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=context_data
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return activity 