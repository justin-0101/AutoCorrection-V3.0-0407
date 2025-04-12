#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery任务基类
提供通用的任务监控、超时控制和错误处理功能
"""

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
import logging
from datetime import datetime
from typing import Any, Dict

# 配置日志记录器
logger = logging.getLogger(__name__)

class BaseTask(Task):
    """
    Celery任务基类
    提供通用的任务监控和错误处理功能
    """
    
    # 任务超时设置
    soft_time_limit = 600  # 10分钟软超时
    time_limit = 660      # 11分钟强制超时
    
    def apply_async(self, *args, **kwargs) -> Any:
        """
        重写任务提交方法，添加任务开始时间记录
        """
        task = super().apply_async(*args, **kwargs)
        logger.info(f"任务已提交 [task_id={task.id}, args={args}, kwargs={kwargs}]")
        return task
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """
        任务成功完成时的回调
        """
        logger.info(f"任务执行成功 [task_id={task_id}, result={retval}]")
        self._record_task_metrics(task_id, "success", args, kwargs)
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """
        任务失败时的回调
        """
        error_msg = f"任务执行失败 [task_id={task_id}, error={str(exc)}]"
        logger.error(error_msg)
        
        # 记录任务指标
        self._record_task_metrics(task_id, "failure", args, kwargs, error=str(exc))
        
        # TODO: 发送告警通知（需要实现具体的告警逻辑）
        self._send_alert(task_id, str(exc), einfo)
    
    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """
        任务重试时的回调
        """
        logger.warning(f"任务将重试 [task_id={task_id}, error={str(exc)}]")
        self._record_task_metrics(task_id, "retry", args, kwargs, error=str(exc))
    
    def _record_task_metrics(self, task_id: str, status: str, args: tuple, kwargs: dict, error: str = None) -> None:
        """
        记录任务执行指标
        
        Args:
            task_id: 任务ID
            status: 任务状态
            args: 任务参数
            kwargs: 任务关键字参数
            error: 错误信息（如果有）
        """
        metrics = {
            "task_id": task_id,
            "task_name": self.name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "args": args,
            "kwargs": kwargs
        }
        
        if error:
            metrics["error"] = error
            
        # TODO: 将指标数据保存到监控系统（需要实现具体的保存逻辑）
        logger.info(f"任务指标记录: {metrics}")
    
    def _send_alert(self, task_id: str, error_msg: str, error_info: Any) -> None:
        """
        发送任务告警
        
        Args:
            task_id: 任务ID
            error_msg: 错误消息
            error_info: 错误详细信息
        """
        alert_data = {
            "task_id": task_id,
            "task_name": self.name,
            "error": error_msg,
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": str(error_info) if error_info else None
        }
        
        # TODO: 实现具体的告警发送逻辑（如发送到Sentry或企业微信）
        logger.error(f"任务告警: {alert_data}") 