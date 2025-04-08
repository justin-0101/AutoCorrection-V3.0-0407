#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务状态模型 - 跟踪异步任务执行状态
"""

import enum
from datetime import datetime, timedelta, UTC
from app.models.db import db, BaseModel
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Enum

class TaskState(enum.Enum):
    """任务状态枚举"""
    PENDING = 'pending'      # 等待执行
    RECEIVED = 'received'    # 已接收
    STARTED = 'started'      # 已开始执行
    SUCCESS = 'success'      # 执行成功
    FAILURE = 'failure'      # 执行失败
    RETRY = 'retry'          # 正在重试
    REVOKED = 'revoked'      # 已撤销
    REJECTED = 'rejected'    # 被拒绝
    
    @classmethod
    def terminal_states(cls):
        """返回所有终止状态"""
        return [cls.SUCCESS, cls.FAILURE, cls.REVOKED, cls.REJECTED]
    
    @classmethod
    def active_states(cls):
        """返回所有活动状态"""
        return [cls.PENDING, cls.RECEIVED, cls.STARTED, cls.RETRY]
    
    def is_terminal(self):
        """判断是否为终止状态"""
        return self in self.terminal_states()
    
    def is_active(self):
        """判断是否为活动状态"""
        return self in self.active_states()


class TaskStatus(BaseModel):
    """任务状态跟踪模型"""
    __tablename__ = 'task_statuses'
    
    task_id = Column(String(50), nullable=False, index=True, comment='Celery任务ID')
    task_name = Column(String(100), nullable=False, index=True, comment='任务名称')
    status = Column(Enum(TaskState), nullable=False, index=True, default=TaskState.PENDING, comment='任务状态')
    
    # 任务结果和错误信息
    result = Column(JSON, nullable=True, comment='任务结果')
    error_message = Column(String(255), nullable=True, comment='错误消息')
    traceback = Column(Text, nullable=True, comment='错误堆栈')
    
    # 重试信息
    retry_count = Column(Integer, default=0, index=True, comment='重试次数')
    max_retries = Column(Integer, default=3, comment='最大重试次数')
    next_retry_at = Column(DateTime, nullable=True, comment='下次重试时间')
    
    # 关联信息
    related_type = Column(String(20), nullable=True, comment='关联对象类型')
    related_id = Column(Integer, nullable=True, comment='关联对象ID')
    worker_id = Column(String(100), nullable=True, comment='执行该任务的Worker ID')
    
    # 元数据
    args = Column(JSON, nullable=True, comment='任务参数')
    kwargs = Column(JSON, nullable=True, comment='任务关键字参数')
    options = Column(JSON, nullable=True, comment='任务选项')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now(UTC), index=True, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), comment='更新时间')
    started_at = Column(DateTime, nullable=True, comment='开始时间')
    completed_at = Column(DateTime, nullable=True, comment='完成时间')
    
    # 优先级
    priority = Column(Integer, default=5, comment='任务优先级(1-10)')
    
    # 创建联合索引
    __table_args__ = (
        db.Index('ix_task_statuses_related', 'related_type', 'related_id'),
        db.Index('ix_task_statuses_status_created_at', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f'<TaskStatus {self.task_id}: {self.status.value}>'
    
    def can_retry(self):
        """判断任务是否可以重试"""
        return (
            self.retry_count < self.max_retries and 
            self.status != TaskState.SUCCESS and
            not self.status.is_terminal()
        )
    
    def mark_as_started(self):
        """标记任务已开始执行"""
        self.status = TaskState.STARTED
        self.started_at = datetime.now(UTC)
        db.session.commit()
    
    def mark_as_success(self, result=None):
        """标记任务执行成功"""
        self.status = TaskState.SUCCESS
        self.completed_at = datetime.now(UTC)
        
        if result is not None:
            self.result = result
            
        db.session.commit()
    
    def mark_as_failure(self, error_message=None, traceback=None):
        """标记任务执行失败"""
        self.status = TaskState.FAILURE
        self.completed_at = datetime.now(UTC)
        
        if error_message is not None:
            self.error_message = error_message
            
        if traceback is not None:
            self.traceback = traceback
            
        db.session.commit()
    
    def mark_as_retry(self, next_retry_at=None, error_message=None, traceback=None):
        """标记任务将进行重试"""
        self.status = TaskState.RETRY
        self.retry_count += 1
        
        if next_retry_at is not None:
            self.next_retry_at = next_retry_at
            
        if error_message is not None:
            self.error_message = error_message
            
        if traceback is not None:
            self.traceback = traceback
            
        db.session.commit()
    
    @classmethod
    def create_from_task(cls, task_id, task_name, **kwargs):
        """从任务创建状态记录"""
        task_status = cls(
            task_id=task_id,
            task_name=task_name,
            status=TaskState.PENDING,
            **kwargs
        )
        db.session.add(task_status)
        db.session.commit()
        return task_status
    
    @classmethod
    def find_by_task_id(cls, task_id):
        """通过任务ID查找状态记录"""
        return cls.query.filter_by(task_id=task_id).first()
    
    @classmethod
    def find_by_related(cls, related_type, related_id):
        """通过关联对象查找状态记录"""
        return cls.query.filter_by(
            related_type=related_type,
            related_id=related_id
        ).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def find_active_tasks(cls):
        """查找所有活动任务"""
        active_states = [state.value for state in TaskState.active_states()]
        return cls.query.filter(cls.status.in_(active_states)).all()
    
    @classmethod
    def find_failed_tasks(cls):
        """查找所有失败任务"""
        return cls.query.filter_by(status=TaskState.FAILURE).all()
    
    @classmethod
    def find_stalled_tasks(cls, older_than=None):
        """查找所有停滞任务"""
        query = cls.query.filter(cls.status.in_([
            TaskState.STARTED.value,
            TaskState.RECEIVED.value,
        ]))
        
        if older_than is not None:
            query = query.filter(cls.updated_at < older_than)
            
        return query.all() 