#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批改工作流程日志模块
用于监控和记录AI批改过程的详细信息
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import traceback
import os
from flask import current_app

logger = logging.getLogger(__name__)

class CorrectionLogger:
    """批改工作流程日志记录器"""
    
    def __init__(self):
        """初始化日志记录器"""
        # 获取应用根目录
        if current_app:
            app_root = current_app.root_path
        else:
            # 如果不在应用上下文中，使用相对路径
            app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        self.log_dir = os.path.join(app_root, 'logs', 'correction')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 配置日志级别
        logger.setLevel(logging.INFO)
        
        # 配置文件处理器
        self.setup_file_handlers()
        
    def setup_file_handlers(self):
        """设置文件处理器"""
        # 工作流程日志
        workflow_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'workflow_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
        workflow_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        workflow_handler.setFormatter(workflow_formatter)
        workflow_handler.setLevel(logging.INFO)
        
        # 性能监控日志
        perf_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'performance_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
        perf_formatter = logging.Formatter(
            '%(asctime)s - PERFORMANCE - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        perf_handler.setFormatter(perf_formatter)
        perf_handler.setLevel(logging.INFO)
        
        # 移除现有的处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 添加新的处理器
        logger.addHandler(workflow_handler)
        logger.addHandler(perf_handler)
        
        # 确保日志立即写入文件
        workflow_handler.flush()
        perf_handler.flush()
    
    def log_correction_start(self, essay_id: str) -> None:
        """记录批改开始"""
        logger.info(f"开始批改作文 [ID: {essay_id}]")
    
    def log_correction_complete(self, essay_id: str, result: Dict[str, Any]) -> None:
        """记录批改完成"""
        if isinstance(result, dict):
            status = result.get("status", "unknown")
            if status == "success":
                logger.info(f"完成批改作文 [ID: {essay_id}] - 状态: 成功")
            else:
                logger.error(f"批改作文失败 [ID: {essay_id}] - 原因: {result.get('message', '未知错误')}")
        else:
            logger.error(f"批改作文失败 [ID: {essay_id}] - 返回结果格式错误")
    
    def log_performance(self, essay_id: str, duration: float) -> None:
        """记录性能数据"""
        logger.info(f"性能统计 [ID: {essay_id}] - 处理时间: {duration:.2f}秒")
    
    def log_error(self, essay_id: str, error: Exception) -> None:
        """记录错误信息"""
        logger.error(
            f"批改过程发生错误 [ID: {essay_id}] - "
            f"错误类型: {type(error).__name__}, "
            f"错误信息: {str(error)}\n"
            f"堆栈跟踪:\n{traceback.format_exc()}"
        )
    
    def monitor_correction(self, func):
        """批改过程监控装饰器"""
        @wraps(func)
        def wrapper(service, essay_id, *args, **kwargs):
            start_time = time.time()
            
            try:
                # 记录开始
                self.log_correction_start(str(essay_id))
                
                # 执行批改
                result = func(service, essay_id, *args, **kwargs)
                
                # 记录完成
                self.log_correction_complete(str(essay_id), result)
                
                # 记录性能
                duration = time.time() - start_time
                self.log_performance(str(essay_id), duration)
                
                return result
                
            except Exception as e:
                # 记录错误
                self.log_error(str(essay_id), e)
                raise
            
        return wrapper

# 创建全局日志记录器实例
correction_logger = CorrectionLogger() 