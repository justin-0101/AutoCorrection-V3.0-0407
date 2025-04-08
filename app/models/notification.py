#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知相关数据模型
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship

from app.models.db import db, BaseModel

class NotificationType(enum.Enum):
    """通知类型枚举"""
    SYSTEM = 'system'        # 系统通知
    ESSAY = 'essay'          # 作文相关
    MEMBERSHIP = 'membership'  # 会员相关
    PAYMENT = 'payment'      # 支付相关
    ACCOUNT = 'account'      # 账户相关

class Notification(BaseModel):
    """通知模型"""
    __tablename__ = 'notifications'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    type = Column(String(50), default=NotificationType.SYSTEM.value)  # system, essay, membership, etc.
    level = Column(String(20))  # info, warning, error
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    extra_data = Column(JSON)  # 额外的元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.title}>'
    
    def mark_as_read(self):
        """标记为已读"""
        self.is_read = True
        self.read_at = datetime.now()
        db.session.commit()
    
    def to_dict(self):
        """将通知转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'content': self.content,
            'type': self.type,
            'level': self.level,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 