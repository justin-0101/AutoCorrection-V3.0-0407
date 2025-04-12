#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库事务工具模块
提供事务管理、超时控制等功能
"""

import logging
from contextlib import contextmanager
from sqlalchemy.orm import Session
from typing import Optional

logger = logging.getLogger(__name__)

@contextmanager
def transaction_timeout(session: Session, timeout_seconds: int = 5):
    """
    设置PostgreSQL事务语句超时的上下文管理器
    
    Args:
        session: SQLAlchemy会话实例
        timeout_seconds: 超时时间（秒），默认5秒
        
    Yields:
        Session: 设置了超时的数据库会话
        
    Examples:
        # 使用5秒超时的事务
        with transaction_timeout(db.session, 5):
            essay = Essay.query.get(1)
            essay.status = 'processing'
            db.session.commit()
    """
    try:
        # 开始事务
        session.execute("BEGIN")
        
        # 设置当前事务的语句超时
        session.execute(f"SET LOCAL statement_timeout = '{timeout_seconds}s'")
        logger.debug(f"设置事务超时: {timeout_seconds}秒")
        
        # 提供会话给调用者
        yield session
        
        # 提交事务
        session.commit()
        logger.debug("事务已提交")
        
    except Exception as e:
        # 发生异常时回滚事务
        session.rollback()
        logger.error(f"事务执行出错，已回滚: {str(e)}")
        raise
    finally:
        # 确保会话干净（不需要调用close，因为session是外部传入的）
        session.execute("SET LOCAL statement_timeout = DEFAULT")


@contextmanager
def essay_update_transaction(session: Session, timeout_seconds: int = 3):
    """
    专门用于作文更新的事务超时管理器
    
    Args:
        session: SQLAlchemy会话实例
        timeout_seconds: 超时时间（秒），默认3秒
        
    Yields:
        Session: 设置了超时的数据库会话
    """
    with transaction_timeout(session, timeout_seconds) as s:
        yield s


@contextmanager
def correction_update_transaction(session: Session, timeout_seconds: int = 3):
    """
    专门用于批改更新的事务超时管理器
    
    Args:
        session: SQLAlchemy会话实例
        timeout_seconds: 超时时间（秒），默认3秒
        
    Yields:
        Session: 设置了超时的数据库会话
    """
    with transaction_timeout(session, timeout_seconds) as s:
        yield s


@contextmanager
def long_operation_transaction(session: Session, timeout_seconds: int = 30):
    """
    用于长时间操作的事务超时管理器
    
    Args:
        session: SQLAlchemy会话实例
        timeout_seconds: 超时时间（秒），默认30秒
        
    Yields:
        Session: 设置了超时的数据库会话
    """
    with transaction_timeout(session, timeout_seconds) as s:
        yield s 