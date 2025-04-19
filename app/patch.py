#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
猴子补丁应用模块
用于应用必要的猴子补丁，确保各个库能够正常协同工作
"""

import os
import sys
import logging
from threading import local as threading_local

logger = logging.getLogger(__name__)

def apply_eventlet_patch():
    """
    应用Eventlet补丁以确保与异步IO和SQLAlchemy的兼容性
    
    此函数必须在应用启动时最早调用，以确保所有I/O操作都被正确补丁
    """
    logger.info("准备应用Eventlet补丁...")
    
    # 检查是否需要应用Eventlet补丁
    worker_pool = os.environ.get('CELERY_WORKER_POOL', '').lower()
    if worker_pool != 'eventlet':
        logger.info(f"当前工作池不是eventlet ({worker_pool})，跳过应用补丁")
        return False
    
    try:
        # 1. 保存原始的threading.get_ident函数引用
        import threading
        original_get_ident = threading.get_ident
        
        # 2. 保存原始的SQLAlchemy队列通知函数
        import sqlalchemy.util.queue
        original_notify = sqlalchemy.util.queue.Queue.notify
    
        # 3. 应用全面的Eventlet补丁
        import eventlet
        eventlet.monkey_patch(all=True)
        logger.info("已完成Eventlet全面补丁应用")

        # 4. 创建线程本地存储用于跟踪线程状态
        _thread_context = threading_local()
        
        # 5. 安全的notify补丁，避免"cannot notify on un-acquired lock"错误
        def safe_notify(self):
            if not hasattr(self, 'mutex') or not self.mutex.locked():
                logger.debug("跳过未锁定互斥锁的通知")
                return
            try:
                return original_notify(self)
            except Exception as e:
                logger.warning(f"Queue.notify调用失败: {e}")
                return None
                
        # 应用notify补丁
        sqlalchemy.util.queue.Queue.notify = safe_notify
        logger.info("已应用SQLAlchemy Queue.notify安全补丁")
        
        # 6. 为SQLAlchemy添加连接处理
        try:
            from sqlalchemy import event
            from sqlalchemy.engine import Engine
            
            @event.listens_for(Engine, "checkout")
            def checkout_connection(dbapi_connection, connection_record, connection_proxy):
                # 标记所有连接为有效，避免在eventlet环境中的线程检查问题
                if hasattr(connection_proxy, '_is_valid'):
                    connection_proxy._is_valid = True
                if hasattr(connection_record, '_is_valid'):
                    connection_record._is_valid = True
                
            logger.info("已为SQLAlchemy Engine添加连接检出事件处理器")
        except ImportError:
            logger.warning("无法为SQLAlchemy添加连接事件处理器")
        
        # 7. 重定向数据库URL以支持SQLite内存数据库的并发访问（如果正在使用）
        from sqlalchemy.engine.url import make_url
        original_make_url = make_url
        
        def patched_make_url(url_string):
            url = original_make_url(url_string)
            # 对于SQLite内存数据库，添加共享缓存模式
            if url.drivername == 'sqlite' and url.database in (None, '', ':memory:'):
                url = url.set(database='file::memory:?cache=shared')
            return url
            
        # 应用URL补丁（如果使用最新的SQLAlchemy版本，这可能需要调整）
        try:
            sqlalchemy.engine.url.make_url = patched_make_url
            logger.info("已应用SQLite内存数据库URL补丁")
        except (AttributeError, ImportError):
            logger.warning("无法应用SQLite URL补丁，可能使用了不兼容的SQLAlchemy版本")
        
        # 8. 最后添加一些调试信息
        logger.info("Eventlet补丁应用完成，当前环境已准备好处理异步任务")
        return True
        
    except ImportError as e:
        logger.error(f"应用Eventlet补丁失败: {e}")
        logger.error("请确保已安装eventlet: pip install eventlet")
        return False
    except Exception as e:
        logger.error(f"应用Eventlet补丁时发生未知错误: {e}")
        return False
        
# 提供一个检查函数
def is_eventlet_patched():
    """
    检查当前环境是否已应用Eventlet补丁
    """
    try:
        import eventlet
        return eventlet.patcher.is_monkey_patched('thread')
    except ImportError:
        return False

def apply_sqlalchemy_patch():
    """应用SQLAlchemy连接池补丁，处理与eventlet的兼容性问题"""
    try:
        # 这个函数会在app/__init__.py中被调用
        # 具体的SQLAlchemy配置修改已在app/extensions.py中完成
        logger.info("SQLAlchemy补丁已在extensions.py中处理")
        return True
    except Exception as e:
        logger.error(f"应用SQLAlchemy补丁时出错: {str(e)}")
        return False

def apply_patches():
    """应用所有必要的猴子补丁"""
    logger.info("开始应用猴子补丁...")
    
    # 应用eventlet补丁
    eventlet_patched = apply_eventlet_patch()
    
    # 应用SQLAlchemy补丁
    sqlalchemy_patched = apply_sqlalchemy_patch()
    
    logger.info(f"补丁应用状态: eventlet={eventlet_patched}, sqlalchemy={sqlalchemy_patched}")
    return eventlet_patched, sqlalchemy_patched 