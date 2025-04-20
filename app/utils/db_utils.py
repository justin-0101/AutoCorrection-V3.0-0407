#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库工具模块
提供数据库操作的辅助函数
"""

import logging
import sqlite3
from typing import List, Dict, Any, Optional, Tuple, Union
from app.database import get_db_path

logger = logging.getLogger(__name__)

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    获取数据库连接
    
    Args:
        db_path: 数据库路径，如果为None则使用默认路径
        
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    if db_path is None:
        db_path = get_db_path()
    
    logger.debug(f"连接到数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
    return conn

def execute_query(
    query: str, 
    params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None, 
    db_path: Optional[str] = None
) -> int:
    """
    执行SQL查询并返回受影响的行数
    
    Args:
        query: SQL查询语句
        params: 查询参数
        db_path: 数据库路径，如果为None则使用默认路径
        
    Returns:
        int: 受影响的行数
    """
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        logger.error(f"执行查询时出错: {str(e)}, 查询: {query}, 参数: {params}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def fetch_all(
    query: str, 
    params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None, 
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    执行查询并获取所有结果行
    
    Args:
        query: SQL查询语句
        params: 查询参数
        db_path: 数据库路径，如果为None则使用默认路径
        
    Returns:
        List[Dict[str, Any]]: 查询结果列表
    """
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        results = cursor.fetchall()
        # 将sqlite3.Row对象转换为字典
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"获取所有结果时出错: {str(e)}, 查询: {query}, 参数: {params}")
        raise
    finally:
        if conn:
            conn.close()

def fetch_one(
    query: str, 
    params: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None, 
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    执行查询并获取单个结果行
    
    Args:
        query: SQL查询语句
        params: 查询参数
        db_path: 数据库路径，如果为None则使用默认路径
        
    Returns:
        Optional[Dict[str, Any]]: 查询结果字典，如果没有结果则返回None
    """
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"获取单行结果时出错: {str(e)}, 查询: {query}, 参数: {params}")
        raise
    finally:
        if conn:
            conn.close() 