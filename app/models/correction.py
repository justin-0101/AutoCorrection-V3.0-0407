#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批改相关数据模型
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.db import db, BaseModel
from app.utils.input_sanitizer import sanitize_input

class CorrectionStatus(str, enum.Enum):
    """批改状态枚举"""
    PENDING = 'pending'       # 等待批改
    CORRECTING = 'correcting' # 正在批改
    COMPLETED = 'completed'   # 批改完成
    FAILED = 'failed'        # 批改失败

    @classmethod
    def get_display_text(cls, status):
        """获取状态的显示文本"""
        status_text = {
            cls.PENDING.value: '等待批改',
            cls.CORRECTING.value: '正在批改',
            cls.COMPLETED.value: '批改完成',
            cls.FAILED.value: '批改失败'
        }
        return status_text.get(status, '未知状态')

class CorrectionType(str, enum.Enum):
    """批改类型枚举"""
    AI = 'ai'      # AI批改
    HUMAN = 'human' # 人工批改

    @classmethod
    def get_display_text(cls, type_):
        """获取类型的显示文本"""
        type_text = {
            cls.AI.value: 'AI批改',
            cls.HUMAN.value: '人工批改'
        }
        return type_text.get(type_, '未知类型')

class Correction(BaseModel):
    """批改记录模型"""
    __tablename__ = 'corrections'
    
    # 添加数据库级别约束
    __table_args__ = (
        db.CheckConstraint(
            "type IN ('ai', 'human')",
            name='valid_correction_type'
        ),
        db.CheckConstraint(
            "status IN ('pending', 'correcting', 'completed', 'failed')",
            name='valid_correction_status'
        ),
    )
    
    essay_id = Column(Integer, ForeignKey('essays.id', ondelete='CASCADE'), nullable=False)
    corrector_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    type = Column(String(20), nullable=False, default=CorrectionType.AI.value)
    content = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    comments = Column(Text, nullable=True)
    error_analysis = Column(JSON, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default=CorrectionStatus.PENDING.value)
    results = Column(JSON, nullable=True)
    task_id = Column(String(36), nullable=True, unique=True)  # Celery任务ID
    error_message = Column(Text, nullable=True)  # 错误信息
    retry_count = Column(Integer, default=0)  # 重试次数
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    
    # 关系
    essay = relationship('Essay', back_populates='corrections', lazy='joined')
    corrector = relationship('User', back_populates='corrections', lazy='joined')
    
    @validates('type')
    def validate_type(self, key, value):
        """验证批改类型"""
        if isinstance(value, CorrectionType):
            return value.value
        return sanitize_input(
            value,
            max_length=20,
            default=CorrectionType.AI.value,
            enum_values=[t.value for t in CorrectionType]
        )
    
    @validates('status')
    def validate_status(self, key, value):
        """验证批改状态"""
        if isinstance(value, CorrectionStatus):
            return value.value
        return sanitize_input(
            value,
            max_length=20,
            default=CorrectionStatus.PENDING.value,
            enum_values=[s.value for s in CorrectionStatus]
        )
    
    def update_status(self, new_status, error_message=None):
        """更新批改状态"""
        if isinstance(new_status, CorrectionStatus):
            new_status = new_status.value
            
        old_status = self.status
        self.status = new_status
        
        if new_status == CorrectionStatus.COMPLETED.value:
            self.completed_at = datetime.utcnow()
        elif new_status == CorrectionStatus.FAILED.value and error_message:
            self.error_message = error_message
            
        # 同步更新Essay状态
        if self.essay:
            self.essay.status = new_status
            if new_status == CorrectionStatus.COMPLETED.value:
                self.essay.corrected_at = self.completed_at
                # 同步批改结果到Essay
                if self.results:
                    self.sync_results_to_essay()
        
        db.session.commit()
        return old_status != new_status
    
    def sync_results_to_essay(self):
        """将批改结果同步到Essay"""
        if not self.results or not self.essay:
            return False
            
        try:
            results = self.results if isinstance(self.results, dict) else {}
            self.essay.score = results.get('score')
            self.essay.corrected_content = results.get('corrected_content')
            self.essay.comments = results.get('comments')
            self.essay.error_analysis = results.get('error_analysis')
            self.essay.improvement_suggestions = results.get('improvement_suggestions')
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def increment_retry(self):
        """增加重试次数"""
        self.retry_count += 1
        db.session.commit()
        return self.retry_count
    
    def __repr__(self):
        return f'<Correction id={self.id}, essay_id={self.essay_id}, type={self.type}, status={self.status}>'
    
    def to_dict(self):
        """将批改记录转换为字典"""
        return {
            'id': self.id,
            'essay_id': self.essay_id,
            'corrector_id': self.corrector_id,
            'type': self.type,
            'type_display': CorrectionType.get_display_text(self.type),
            'content': self.content,
            'score': self.score,
            'comments': self.comments,
            'error_analysis': self.error_analysis,
            'improvement_suggestions': self.improvement_suggestions,
            'status': self.status,
            'status_display': CorrectionStatus.get_display_text(self.status),
            'results': self.results,
            'task_id': self.task_id,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
