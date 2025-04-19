#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import json
from app.extensions import db
from app.models.task_status import TaskStatus, TaskState

class Task:
    """
    Task是TaskStatus的简单包装，提供与Celery任务状态兼容的API
    这个类不是数据库模型，而是提供统一的任务状态查询接口
    """
    
    def __init__(self, task_id=None, task_status=None):
        self.id = task_id
        if task_status:
            self._task_status = task_status
        elif task_id:
            self._task_status = TaskStatus.query.filter_by(task_id=task_id).first()
        else:
            self._task_status = None
    
    @property
    def status(self):
        """与Celery任务状态兼容的任务状态"""
        if not self._task_status:
            return 'PENDING'
            
        # 映射TaskStatus的状态到Celery兼容的状态
        status_map = {
            TaskState.PENDING: 'PENDING',
            TaskState.RUNNING: 'STARTED',
            TaskState.SUCCESS: 'SUCCESS',
            TaskState.FAILED: 'FAILURE',
            TaskState.RETRY: 'RETRY',
            TaskState.CANCELLED: 'REVOKED'
        }
        
        return status_map.get(self._task_status.status, 'PENDING')
    
    @property
    def error(self):
        """任务错误信息"""
        if not self._task_status:
            return None
        return self._task_status.error
    
    @property
    def result(self):
        """任务结果"""
        if not self._task_status:
            return None
        return self._task_status.result
    
    @property
    def created_at(self):
        """任务创建时间"""
        if not self._task_status:
            return None
        return self._task_status.created_at
    
    @property
    def completed_at(self):
        """任务完成时间"""
        if not self._task_status:
            return None
        return self._task_status.completed_at
    
    @property
    def duration(self):
        """任务执行时长"""
        if not self._task_status:
            return None
        return self._task_status.duration
    
    @classmethod
    def query(cls):
        """提供类似于SQLAlchemy查询接口的方法"""
        return TaskQuery(cls)
        
class TaskQuery:
    """模拟SQLAlchemy查询接口的简单查询类"""
    
    def __init__(self, task_cls):
        self.task_cls = task_cls
        self._query = TaskStatus.query
        
    def filter_by(self, **kwargs):
        """按条件过滤"""
        self._query = self._query.filter_by(**kwargs)
        return self
        
    def first(self):
        """获取第一个结果"""
        task_status = self._query.first()
        if not task_status:
            return None
        return self.task_cls(task_id=task_status.task_id, task_status=task_status)
        
    def all(self):
        """获取所有结果"""
        task_statuses = self._query.all()
        return [self.task_cls(task_id=ts.task_id, task_status=ts) for ts in task_statuses] 