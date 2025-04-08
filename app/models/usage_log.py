#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用记录相关数据模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.models.db import db, BaseModel

class UsageLog(BaseModel):
    """使用记录模型"""
    __tablename__ = 'usage_logs'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String(50))  # essay_submission, ai_correction, human_correction, etc.
    resource_id = Column(Integer)  # 相关资源ID（如作文ID）
    resource_type = Column(String(50))  # 资源类型（如essay, correction等）
    description = Column(Text)  # 使用描述
    extra_data = Column(JSON)  # 额外的元数据
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship('User', backref='usage_logs')
    
    def __repr__(self):
        return f'<UsageLog {self.id}>'
    
    def to_dict(self):
        """将使用记录转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'description': self.description,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @staticmethod
    def create_log(user_id, event_type, resource_id=None, metadata=None):
        """
        创建使用日志
        
        Args:
            user_id: 用户ID
            event_type: 事件类型
            resource_id: 相关资源ID（可选）
            metadata: 事件元数据（可选）
            
        Returns:
            UsageLog: 创建的日志记录
        """
        from app.models.membership import Membership
        
        # 获取用户当前会员信息
        membership = Membership.query.filter_by(user_id=user_id).first()
        membership_id = membership.id if membership else None
        
        # 创建日志记录
        log = UsageLog(
            user_id=user_id,
            type=event_type,
            resource_id=resource_id,
            resource_type=None,
            description=None,
            extra_data=metadata or {},
            created_at=datetime.utcnow().timestamp()
        )
        
        # 保存到数据库
        db.session.add(log)
        db.session.commit()
        
        return log
    
    @staticmethod
    def get_user_logs(user_id, start_date=None, end_date=None, event_type=None, limit=100):
        """
        获取用户使用日志
        
        Args:
            user_id: 用户ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            event_type: 事件类型（可选）
            limit: 记录数量限制
            
        Returns:
            List[UsageLog]: 用户使用日志列表
        """
        query = UsageLog.query.filter_by(user_id=user_id)
        
        if start_date:
            query = query.filter(UsageLog.created_at >= start_date.timestamp())
        
        if end_date:
            query = query.filter(UsageLog.created_at <= end_date.timestamp())
        
        if event_type:
            query = query.filter_by(type=event_type)
        
        return query.order_by(db.desc(UsageLog.created_at)).limit(limit).all()
    
    @staticmethod
    def get_event_stats(event_type, start_date=None, end_date=None):
        """
        获取事件统计
        
        Args:
            event_type: 事件类型
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            Dict: 事件统计信息
        """
        query = UsageLog.query.filter_by(type=event_type)
        
        if start_date:
            query = query.filter(UsageLog.created_at >= start_date.timestamp())
        
        if end_date:
            query = query.filter(UsageLog.created_at <= end_date.timestamp())
        
        # 总数统计
        total_count = query.count()
        
        # 用户数统计
        unique_users = db.session.query(db.func.count(db.distinct(UsageLog.user_id))).filter(
            UsageLog.type == event_type
        )
        
        if start_date:
            unique_users = unique_users.filter(UsageLog.created_at >= start_date.timestamp())
        
        if end_date:
            unique_users = unique_users.filter(UsageLog.created_at <= end_date.timestamp())
        
        unique_users_count = unique_users.scalar()
        
        return {
            "total_count": total_count,
            "unique_users": unique_users_count
        } 