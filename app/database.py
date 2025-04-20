#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库工具模块
提供数据库路径和连接管理相关功能
"""

import os
import logging
import sqlite3
from pathlib import Path
from flask import current_app, g

logger = logging.getLogger(__name__)

def get_db_path():
    """获取数据库路径
    
    Returns:
        str: 数据库文件的绝对路径
    """
    # 尝试从Flask应用配置获取数据库路径
    if current_app and current_app.config.get('SQLALCHEMY_DATABASE_URI'):
        database_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        if database_uri.startswith('sqlite:///'):
            return database_uri[10:]
    
    # 如果没有获取到，使用默认路径
    project_root = Path(__file__).resolve().parent.parent
    db_path = os.path.join(project_root, 'instance', 'essay_correction.db')
    
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    logger.debug(f"使用数据库路径: {db_path}")
    return db_path

def get_db_connection():
    """获取SQLite数据库连接
    
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    db_path = get_db_path()
    
    # 如果在Flask应用上下文中，使用g对象存储连接
    if 'g' in globals() or 'g' in locals():
        if not hasattr(g, 'db_connection'):
            g.db_connection = sqlite3.connect(db_path)
            g.db_connection.row_factory = sqlite3.Row
        return g.db_connection
    
    # 否则直接创建新连接
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def close_db_connection(e=None):
    """关闭数据库连接
    
    Args:
        e: 可选的异常对象
    """
    db_conn = g.pop('db_connection', None)
    
    if db_conn is not None:
        db_conn.close() 