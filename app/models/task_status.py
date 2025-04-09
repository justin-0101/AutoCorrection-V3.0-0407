#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import json
from enum import Enum
from app.extensions import db
from sqlalchemy import JSON

class TaskState(str, Enum):
    """任务状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    RETRY = 'retry'
    CANCELLED = 'cancelled'

class TaskStatus(db.Model):
    """任务状态跟踪模型"""
    __tablename__ = 'task_status'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    task_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=TaskState.PENDING)
    related_type = db.Column(db.String(50))  # essay, batch, etc.
    related_id = db.Column(db.String(36), index=True)
    worker_id = db.Column(db.String(100))
    
    # 任务参数和结果
    args = db.Column(db.Text)
    kwargs = db.Column(db.Text)
    result = db.Column(JSON)
    error = db.Column(db.Text)
    
    # 任务元数据
    task_metadata = db.Column(JSON)
    retry_count = db.Column(db.Integer, default=0)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<TaskStatus {self.task_id} ({self.status})>'
    
    @classmethod
    def create_from_task(cls, task_id, task_name, related_type=None, related_id=None,
                        args=None, kwargs=None, worker_id=None):
        """从Celery任务创建状态记录"""
        task = cls(
            task_id=task_id,
            task_name=task_name,
            related_type=related_type,
            related_id=related_id,
            args=args,
            kwargs=kwargs if kwargs else None,
            worker_id=worker_id,
            status=TaskState.PENDING
        )
        db.session.add(task)
        db.session.commit()
        return task
    
    def mark_as_started(self):
        """标记任务为开始状态"""
        self.status = TaskState.RUNNING
        self.started_at = datetime.utcnow()
        db.session.commit()
    
    def mark_as_success(self, result=None):
        """标记任务为成功状态"""
        self.status = TaskState.SUCCESS
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result if isinstance(result, dict) else {'result': result}
        db.session.commit()
    
    def mark_as_failure(self, error=None):
        """标记任务为失败状态"""
        self.status = TaskState.FAILED
        self.completed_at = datetime.utcnow()
        if error:
            self.error = str(error)
        db.session.commit()
    
    def update_metadata(self, metadata):
        """更新任务元数据"""
        current_metadata = self.task_metadata or {}
        current_metadata.update(metadata)
        self.task_metadata = current_metadata
        db.session.commit()
    
    def increment_retry(self):
        """增加重试次数"""
        self.retry_count += 1
        self.status = TaskState.RETRY
        db.session.commit()
    
    @property
    def duration(self):
        """计算任务执行时长（秒）"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    @classmethod
    def get_active_tasks(cls):
        """获取所有活动任务"""
        return cls.query.filter(cls.status.in_([TaskState.PENDING, TaskState.RUNNING])).all()
    
    @classmethod
    def get_task_stats(cls, task_name=None, time_range=None):
        """获取任务统计信息"""
        query = cls.query
        if task_name:
            query = query.filter_by(task_name=task_name)
        if time_range:
            query = query.filter(cls.created_at >= time_range[0],
                               cls.created_at <= time_range[1])
        
        total = query.count()
        success = query.filter_by(status=TaskState.SUCCESS).count()
        failed = query.filter_by(status=TaskState.FAILED).count()
        running = query.filter_by(status=TaskState.RUNNING).count()
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'running': running,
            'success_rate': (success / total * 100) if total > 0 else 0
        }
