#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库核心模块
提供数据库会话管理和通用数据库操作功能
"""

from app.core.db.session_manager import init_session_manager, get_session, get_session_manager

# 全局会话管理器实例 - 将在应用初始化时被设置
session_manager = None

__all__ = ['session_manager', 'init_session_manager', 'get_session', 'get_session_manager'] 