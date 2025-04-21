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
import logging
from sqlalchemy.exc import SQLAlchemyError

# 创建logger实例
logger = logging.getLogger(__name__)

from app.models.db import db, BaseModel
from app.utils.input_sanitizer import sanitize_input

class CorrectionStatus(str, enum.Enum):
    """批改状态枚举"""
    PENDING = 'pending'       # 等待批改
    PROCESSING = 'processing' # 正在提交处理中（临时状态）
    CORRECTING = 'correcting' # 正在批改
    COMPLETED = 'completed'   # 批改完成
    FAILED = 'failed'        # 批改失败

    @classmethod
    def get_display_text(cls, status):
        """获取状态的显示文本"""
        status_text = {
            cls.PENDING.value: '等待批改',
            cls.PROCESSING.value: '正在提交处理中',
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
            "status IN ('pending', 'processing', 'correcting', 'completed', 'failed')",
            name='valid_correction_status'
        ),
        # 添加唯一索引，确保每篇文章只能有一条未删除的correction记录
        db.Index(
            'uix_corrections_essay_active', 
            'essay_id', 
            'is_deleted', 
            unique=True,
            postgresql_where=db.text('is_deleted = false'),  # PostgreSQL支持条件索引
            sqlite_where=db.text('is_deleted = 0')           # SQLite支持条件索引
        ),
    )
    
    # 添加版本控制字段
    version = Column(Integer, default=0, nullable=False)
    
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
    is_deleted = Column(Boolean, nullable=False, default=False)  # 添加默认值
    
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
            
        # 验证状态转换的合法性
        valid_transitions = {
            CorrectionStatus.PENDING.value: [CorrectionStatus.PROCESSING.value, CorrectionStatus.CORRECTING.value, CorrectionStatus.FAILED.value],
            CorrectionStatus.PROCESSING.value: [CorrectionStatus.CORRECTING.value, CorrectionStatus.FAILED.value, CorrectionStatus.PENDING.value],
            CorrectionStatus.CORRECTING.value: [CorrectionStatus.COMPLETED.value, CorrectionStatus.FAILED.value],
            CorrectionStatus.COMPLETED.value: [],  # 完成状态是终态
            CorrectionStatus.FAILED.value: [CorrectionStatus.PENDING.value, CorrectionStatus.PROCESSING.value]  # 允许重试
        }
        
        old_status = self.status
        
        # 检查状态转换是否有效
        if old_status not in valid_transitions:
            logger.error(f"批改记录当前状态无效: {old_status}")
            return False
            
        if new_status not in valid_transitions[old_status]:
            logger.error(f"批改记录状态转换无效: {old_status} -> {new_status}")
            return False
            
        try:
            # 更新状态
            self.status = new_status
            
            # 更新相关字段
            if new_status == CorrectionStatus.COMPLETED.value:
                self.completed_at = datetime.utcnow()
            elif new_status == CorrectionStatus.FAILED.value and error_message:
                self.error_message = error_message
                
            # 同步更新Essay状态 - 改为动态使用essay对象，避免导入Essay类
            if self.essay:
                # 动态获取EssayStatus相关值，以避免循环导入
                if new_status == CorrectionStatus.COMPLETED.value:
                    # 对应EssayStatus.COMPLETED
                    essay_new_status = 'completed'
                elif new_status == CorrectionStatus.FAILED.value:
                    # 对应EssayStatus.FAILED
                    essay_new_status = 'failed'
                elif new_status == CorrectionStatus.CORRECTING.value:
                    # 对应EssayStatus.CORRECTING
                    essay_new_status = 'correcting'
                elif new_status == CorrectionStatus.PROCESSING.value:
                    # 对应EssayStatus.PROCESSING
                    essay_new_status = 'processing'
                elif new_status == CorrectionStatus.PENDING.value:
                    # 对应EssayStatus.PENDING
                    essay_new_status = 'pending'
                else:
                    essay_new_status = None
                    
                if essay_new_status:
                    # 使用essay对象原有的update_status方法
                    self.essay.update_status(essay_new_status, error_message)
                    
                    if new_status == CorrectionStatus.COMPLETED.value:
                        # 同步批改结果到Essay - 使用essay对象上的方法
                        if self.results:
                            self.sync_results_to_essay()
            
            db.session.commit()
            logger.info(f"批改记录 {self.id} 状态已更新: {old_status} -> {new_status}")
            return True
        except Exception as e:
            logger.error(f"更新批改状态时出错: {str(e)}")
            db.session.rollback()
            return False
    
    def sync_results_to_essay(self):
        """将批改结果同步到Essay"""
        if not self.results or not self.essay:
            return False
            
        try:
            results = self.results if isinstance(self.results, dict) else {}
            
            # 同步基本字段
            self.essay.score = results.get('score') or results.get('total_score')
            self.essay.corrected_content = results.get('corrected_content')
            self.essay.comments = results.get('comments')
            self.essay.error_analysis = results.get('error_analysis')
            self.essay.improvement_suggestions = results.get('improvement_suggestions')
            self.essay.corrected_at = datetime.utcnow()
            
            # AI结果字段
            self.essay.ai_score = results.get('score') or results.get('total_score')
            self.essay.ai_comments = results.get('comments')
            self.essay.ai_analysis = results.get('error_analysis')
            
            # 更新批改次数
            self.essay.correction_count = (self.essay.correction_count or 0) + 1
            
            # 更新字数统计如果之前没有
            if not self.essay.word_count and 'word_count' in results:
                self.essay.word_count = results.get('word_count')
                
            db.session.commit()
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
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_deleted': self.is_deleted
        }

    def optimistic_update(self, **kwargs):
        """
        乐观锁更新方法
        
        Args:
            **kwargs: 要更新的字段和值
            
        Returns:
            bool: 更新是否成功
            
        Raises:
            ConcurrentUpdateError: 当版本不匹配时抛出
        """
        try:
            current_version = self.version
            kwargs['version'] = current_version + 1
            
            # 使用版本号作为条件进行更新
            rows = db.session.query(Correction).filter(
                Correction.id == self.id,
                Correction.version == current_version
            ).update(kwargs)
            
            if rows == 0:
                db.session.rollback()
                raise ConcurrentUpdateError("数据已被其他进程修改")
            
            # 更新成功，同步当前对象的版本号
            self.version = current_version + 1
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise DatabaseError(f"数据库更新失败: {str(e)}")
    
    def safe_update_status(self, new_status: str) -> bool:
        """
        安全地更新批改状态
        
        Args:
            new_status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            return self.optimistic_update(
                status=new_status,
                updated_at=datetime.utcnow()
            )
        except ConcurrentUpdateError:
            logger.warning(f"批改状态更新冲突 [id={self.id}, status={new_status}]")
            return False
