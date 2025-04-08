#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库事务管理模块
提供事务控制和管理功能
"""

import functools
import logging
import threading
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app, g

logger = logging.getLogger(__name__)

# 线程本地存储，用于跟踪事务状态
_transaction_local = threading.local()

@contextmanager
def atomic_operation(operation_name=None):
    """
    原子操作上下文管理器
    
    Args:
        operation_name: 操作名称，用于日志记录
        
    Yields:
        session: 数据库会话对象
    """
    from app.core.db import session_manager
    session = session_manager.session
    
    operation_name = operation_name or "数据库操作"
    logger.debug(f"开始{operation_name}")
    
    try:
        yield session
        session.commit()
        logger.debug(f"{operation_name}成功完成")
    except Exception as e:
        session.rollback()
        logger.error(f"{operation_name}失败: {str(e)}")
        raise

def transactional(func):
    """
    事务装饰器
    将函数包装在事务中执行
    
    Args:
        func: 要装饰的函数
        
    Returns:
        函数: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from app.core.db import session_manager
        
        with atomic_operation(f"函数 {func.__name__}"):
            return func(*args, **kwargs)
    return wrapper

def in_transaction(func):
    """
    标记函数在已有事务中执行
    不创建新事务，假定已存在事务
    
    Args:
        func: 要装饰的函数
        
    Returns:
        函数: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 设置事务标记
        if not hasattr(_transaction_local, 'in_transaction'):
            _transaction_local.in_transaction = True
            was_empty = True
        else:
            was_empty = False
            
        try:
            return func(*args, **kwargs)
        finally:
            # 只有当本函数设置了标记，才清除它
            if was_empty:
                delattr(_transaction_local, 'in_transaction')
    return wrapper

def ensure_in_transaction(func):
    """
    确保函数在事务中执行
    如果没有事务则创建新事务
    
    Args:
        func: 要装饰的函数
        
    Returns:
        函数: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if hasattr(_transaction_local, 'in_transaction'):
            # 已在事务中，直接执行
            return func(*args, **kwargs)
        else:
            # 创建新事务
            return transactional(func)(*args, **kwargs)
    return wrapper

def flush_changes():
    """
    刷新当前会话中的更改到数据库
    不提交事务
    
    Returns:
        bool: 是否成功刷新
    """
    from app.core.db import session_manager
    return session_manager.flush()

# 创建事务上下文管理器别名
transaction = atomic_operation

# 初始化模块 - 注册到Flask应用上下文
def init_transaction():
    """初始化事务管理模块"""
    logger.info("事务管理系统已初始化")
    return True 