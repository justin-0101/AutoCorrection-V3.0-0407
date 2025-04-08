#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库会话管理模块
提供数据库会话的创建、管理和访问功能
"""

import logging
from contextlib import contextmanager
from typing import Optional, Any, Dict, List, Iterator

from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# 全局会话管理器实例
_session_manager = None  # type: Optional[SessionManager]

class SessionManager:
    """数据库会话管理器"""
    
    def __init__(self, app=None):
        """
        初始化会话管理器
        
        Args:
            app: Flask应用实例
        """
        self._session_factory = None
        self._scoped_session = None
        self._engine = None
        self._initialized = False
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        使用Flask应用初始化会话管理器
        
        Args:
            app: Flask应用实例
        """
        try:
            # 从应用配置获取数据库URI
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
            if not db_uri:
                raise ValueError("未配置数据库URI，无法初始化会话管理器")
            
            # 创建引擎
            self._engine = create_engine(
                db_uri,
                pool_size=app.config.get('SQLALCHEMY_POOL_SIZE', 5),
                max_overflow=app.config.get('SQLALCHEMY_MAX_OVERFLOW', 10),
                pool_timeout=app.config.get('SQLALCHEMY_POOL_TIMEOUT', 30),
                pool_recycle=app.config.get('SQLALCHEMY_POOL_RECYCLE', 3600),
                echo=app.config.get('SQLALCHEMY_ECHO', False)
            )
            
            # 创建会话工厂
            self._session_factory = sessionmaker(bind=self._engine)
            
            # 创建线程局部会话
            self._scoped_session = scoped_session(self._session_factory)
            
            # 标记为已初始化
            self._initialized = True
            
            # 设置全局实例
            global _session_manager
            _session_manager = self
            
            logger.info("会话管理器初始化完成")
            
            # 清理资源的回调函数
            @app.teardown_appcontext
            def remove_session(exception=None):
                self.remove()
                
        except Exception as e:
            logger.error(f"会话管理器初始化失败: {str(e)}")
            raise
    
    @property
    def session(self) -> Session:
        """
        获取当前会话
        
        Returns:
            Session: 当前会话
        
        Raises:
            RuntimeError: 如果会话管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("会话管理器未初始化")
        return self._scoped_session()
    
    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """
        创建事务上下文
        
        Yields:
            Session: 当前会话
            
        Raises:
            Exception: 如果事务中出现异常
        """
        session = self.session
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"事务回滚: {str(e)}")
            raise
    
    def commit(self) -> bool:
        """
        提交当前会话
        
        Returns:
            bool: 是否成功提交
        """
        try:
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"提交失败: {str(e)}")
            return False
    
    def rollback(self) -> bool:
        """
        回滚当前会话
        
        Returns:
            bool: 是否成功回滚
        """
        try:
            self.session.rollback()
            return True
        except SQLAlchemyError as e:
            logger.error(f"回滚失败: {str(e)}")
            return False
    
    def add(self, instance) -> bool:
        """
        添加对象到会话
        
        Args:
            instance: 要添加的对象实例
            
        Returns:
            bool: 是否成功添加
        """
        try:
            self.session.add(instance)
            return True
        except SQLAlchemyError as e:
            logger.error(f"添加对象失败: {str(e)}")
            return False
    
    def delete(self, instance) -> bool:
        """
        从会话中删除对象
        
        Args:
            instance: 要删除的对象实例
            
        Returns:
            bool: 是否成功删除
        """
        try:
            self.session.delete(instance)
            return True
        except SQLAlchemyError as e:
            logger.error(f"删除对象失败: {str(e)}")
            return False
    
    def remove(self):
        """移除当前会话"""
        if self._initialized and self._scoped_session:
            self._scoped_session.remove()
    
    def close(self):
        """关闭当前会话"""
        if self._initialized and self._scoped_session:
            self._scoped_session().close()
    
    def flush(self) -> bool:
        """
        刷新当前会话中的更改到数据库，但不提交事务
        用于在事务中验证约束或获取自动生成的ID
        
        Returns:
            bool: 是否成功刷新
        """
        try:
            self.session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"刷新会话失败: {str(e)}")
            return False
    
    @staticmethod
    def get_instance() -> 'SessionManager':
        """
        获取会话管理器实例
        
        Returns:
            SessionManager: 会话管理器实例
            
        Raises:
            RuntimeError: 如果会话管理器未初始化
        """
        if _session_manager is None or not _session_manager._initialized:
            raise RuntimeError("会话管理器未初始化，请先调用init_app")
        return _session_manager

# 创建全局访问函数
def get_session_manager() -> SessionManager:
    """
    获取会话管理器实例
    
    Returns:
        SessionManager: 会话管理器实例
    """
    return SessionManager.get_instance()

def get_session() -> Session:
    """
    获取当前会话
    
    Returns:
        Session: 当前数据库会话
    """
    return get_session_manager().session

# 初始化函数 - 由Flask应用调用
def init_session_manager(app):
    """
    初始化会话管理器
    
    Args:
        app: Flask应用实例
        
    Returns:
        bool: 是否成功初始化
    """
    try:
        if _session_manager is None or not _session_manager._initialized:
            SessionManager(app)
        return True
    except Exception as e:
        logger.error(f"初始化会话管理器失败: {str(e)}")
        return False 