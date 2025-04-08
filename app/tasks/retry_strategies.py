#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重试策略模块
提供任务重试的智能决策和退避计算
"""

import logging
import time
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 不应重试的异常类型
NON_RETRIABLE_EXCEPTIONS = (
    ValueError,     # 值错误通常表示输入参数问题
    TypeError,      # 类型错误通常是代码问题
    KeyError,       # 键错误通常是代码问题
    IndexError,     # 索引错误通常是代码问题
    SyntaxError,    # 语法错误
    NameError,      # 名称错误
    ZeroDivisionError,  # 除零错误
)

# 应当重试的异常类型
RETRIABLE_EXCEPTIONS = (
    ConnectionError,  # 连接错误
    TimeoutError,     # 超时错误
    AttributeError,   # 属性错误(可能是模型定义问题)
    IOError,          # IO错误
    OSError,          # 操作系统错误
)

def should_retry_task(exception, retry_count=0, max_retries=3):
    """
    根据异常类型决定是否应当重试任务
    
    Args:
        exception: 捕获的异常
        retry_count: 当前重试次数
        max_retries: 最大重试次数
        
    Returns:
        bool: 是否应该重试
    """
    # 超过最大重试次数
    if retry_count >= max_retries:
        logger.info(f"任务已达到最大重试次数 {max_retries}，不再重试")
        return False
    
    # 检查是否为明确不应重试的异常
    if isinstance(exception, NON_RETRIABLE_EXCEPTIONS):
        logger.info(f"异常 {type(exception).__name__} 属于不可重试类型，不进行重试")
        return False
    
    # 检查是否为明确应当重试的异常
    if isinstance(exception, RETRIABLE_EXCEPTIONS):
        logger.info(f"异常 {type(exception).__name__} 属于可重试类型，将进行重试")
        return True
    
    # 异常消息中的特定关键词
    error_message = str(exception).lower()
    
    # 包含连接相关错误的消息
    if any(keyword in error_message for keyword in ('connection', 'timeout', 'network', 'socket')):
        logger.info(f"异常消息 '{error_message}' 包含连接相关错误，将进行重试")
        return True
    
    # 临时错误相关的消息
    if any(keyword in error_message for keyword in ('temporary', 'transient', 'retry', 'again')):
        logger.info(f"异常消息 '{error_message}' 表明是临时错误，将进行重试")
        return True
    
    # 默认行为：重试第一次，之后根据异常类型决定
    if retry_count == 0:
        logger.info(f"首次遇到异常 {type(exception).__name__}，尝试进行首次重试")
        return True
    
    # 对于未明确分类的异常，不重试
    logger.info(f"异常 {type(exception).__name__} 未明确分类为可重试，不进行重试")
    return False

def exponential_backoff(retry_count, base_delay=3, max_delay=300, jitter=True):
    """
    计算指数退避延迟
    
    Args:
        retry_count: 当前重试次数
        base_delay: 基础延迟(秒)
        max_delay: 最大延迟(秒)
        jitter: 是否添加随机抖动
        
    Returns:
        int: 延迟秒数
    """
    # 指数增长: base_delay * 2^retry_count
    delay = base_delay * (2 ** retry_count)
    
    # 确保不超过最大延迟
    delay = min(delay, max_delay)
    
    # 添加随机抖动(上下10%)
    if jitter:
        jitter_range = delay * 0.1
        delay = delay + random.uniform(-jitter_range, jitter_range)
    
    logger.debug(f"计算的重试延迟: {delay:.2f}秒 (重试次数: {retry_count})")
    return delay

def calculate_next_retry_time(retry_count, base_delay=3, max_delay=300, jitter=True):
    """
    计算下次重试时间
    
    Args:
        retry_count: 当前重试次数
        base_delay: 基础延迟(秒)
        max_delay: 最大延迟(秒)
        jitter: 是否添加随机抖动
        
    Returns:
        datetime: 下次重试时间
    """
    delay = exponential_backoff(retry_count, base_delay, max_delay, jitter)
    return datetime.utcnow() + timedelta(seconds=delay)

def get_retry_policy(task_name=None, exception=None):
    """
    获取特定任务的重试策略
    
    Args:
        task_name: 任务名称
        exception: 异常类型
        
    Returns:
        dict: 重试策略配置
    """
    # 默认重试策略
    default_policy = {
        'max_retries': 3,
        'base_delay': 3,
        'max_delay': 300,
        'jitter': True,
    }
    
    # 针对特定任务的重试策略
    task_specific_policies = {
        'app.tasks.correction_tasks.process_essay_correction': {
            'max_retries': 5,
            'base_delay': 5,
            'max_delay': 600,
        },
        'app.tasks.email_tasks.send_email': {
            'max_retries': 8,
            'base_delay': 10,
            'max_delay': 1800,  # 30分钟
        },
        'app.tasks.backup_tasks': {
            'max_retries': 2,
            'base_delay': 60,
        }
    }
    
    # 针对特定异常的重试策略
    exception_specific_policies = {
        'ConnectionError': {
            'max_retries': 10,
            'base_delay': 15,
            'max_delay': 1800,
        },
        'TimeoutError': {
            'max_retries': 6,
            'base_delay': 30,
            'max_delay': 1200,
        }
    }
    
    policy = default_policy.copy()
    
    # 应用任务特定策略
    if task_name and task_name in task_specific_policies:
        policy.update(task_specific_policies[task_name])
    
    # 应用异常特定策略
    if exception:
        exception_name = type(exception).__name__
        if exception_name in exception_specific_policies:
            # 不完全覆盖任务特定策略，只更新异常相关部分
            for key, value in exception_specific_policies[exception_name].items():
                # 只有在当前策略没有更高值的情况下才应用
                if key == 'max_retries' and policy.get(key, 0) < value:
                    policy[key] = value
                elif key in ('base_delay', 'max_delay') and policy.get(key, 0) < value:
                    policy[key] = value
                else:
                    policy[key] = value
    
    return policy 