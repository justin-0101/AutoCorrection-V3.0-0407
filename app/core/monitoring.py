#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
监控模块
收集和导出系统各类运行指标
"""

import logging
from prometheus_client import Counter, Histogram, Gauge, Info, Summary
import time
import functools

logger = logging.getLogger(__name__)

# 作文来源类型统计
ESSAY_SOURCE_TYPE_COUNTER = Counter(
    'essay_source_types_total',
    '各来源类型的作文提交统计',
    ['source_type']
)

# 作文处理时间直方图
ESSAY_PROCESSING_TIME = Histogram(
    'essay_processing_seconds',
    '作文处理所需时间（秒）',
    ['operation']
)

# 错误计数器
ERROR_COUNTER = Counter(
    'app_errors_total',
    '应用错误计数',
    ['module', 'error_type']
)

# 活跃用户数
ACTIVE_USERS = Gauge(
    'app_active_users',
    '当前活跃用户数'
)

# 系统信息
SYSTEM_INFO = Info(
    'app_system_info',
    '应用系统信息'
)

# 批改性能摘要
CORRECTION_PERFORMANCE = Summary(
    'essay_correction_seconds',
    '批改作文所需时间摘要',
    ['ai_model']
)

def track_source_type(source_type):
    """
    跟踪作文来源类型
    
    参数:
        source_type: 作文来源类型
    """
    try:
        ESSAY_SOURCE_TYPE_COUNTER.labels(source_type=source_type).inc()
    except Exception as e:
        logger.error(f"跟踪来源类型指标失败: {str(e)}")
        
def track_error(module, error_type):
    """
    跟踪应用错误
    
    参数:
        module: 发生错误的模块
        error_type: 错误类型
    """
    try:
        ERROR_COUNTER.labels(module=module, error_type=error_type).inc()
    except Exception as e:
        logger.error(f"跟踪错误指标失败: {str(e)}")

def timing_histogram(operation):
    """
    测量操作执行时间的装饰器
    
    参数:
        operation: 操作名称
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            try:
                ESSAY_PROCESSING_TIME.labels(operation=operation).observe(execution_time)
            except Exception as e:
                logger.error(f"记录执行时间指标失败: {str(e)}")
            return result
        return wrapped_func
    return decorator

def init_system_info(app_version, env_type):
    """
    初始化系统信息
    
    参数:
        app_version: 应用版本
        env_type: 环境类型（dev/test/prod）
    """
    try:
        SYSTEM_INFO.info({
            'version': app_version,
            'environment': env_type
        })
    except Exception as e:
        logger.error(f"初始化系统信息指标失败: {str(e)}")

def track_correction_time(ai_model, execution_time):
    """
    跟踪批改执行时间
    
    参数:
        ai_model: AI模型名称
        execution_time: 执行时间（秒）
    """
    try:
        CORRECTION_PERFORMANCE.labels(ai_model=ai_model).observe(execution_time)
    except Exception as e:
        logger.error(f"跟踪批改性能指标失败: {str(e)}")

def increase_active_users():
    """增加活跃用户计数"""
    try:
        ACTIVE_USERS.inc()
    except Exception as e:
        logger.error(f"增加活跃用户计数失败: {str(e)}")

def decrease_active_users():
    """减少活跃用户计数"""
    try:
        ACTIVE_USERS.dec()
    except Exception as e:
        logger.error(f"减少活跃用户计数失败: {str(e)}")

# 注册到应用的初始化函数
def setup_monitoring(app):
    """
    设置监控
    
    参数:
        app: Flask应用实例
    """
    try:
        from prometheus_client import make_wsgi_app
        from werkzeug.middleware.dispatcher import DispatcherMiddleware
        
        # 从应用配置中获取版本和环境
        app_version = app.config.get('APP_VERSION', '1.0.0')
        env_type = app.config.get('ENVIRONMENT', 'development')
        
        # 初始化系统信息
        init_system_info(app_version, env_type)
        
        # 添加Prometheus WSGI中间件
        app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
            '/metrics': make_wsgi_app()
        })
        
        logger.info("Prometheus监控已设置，指标可在/metrics路径访问")
        return True
    except Exception as e:
        logger.error(f"设置监控失败: {str(e)}")
        return False 