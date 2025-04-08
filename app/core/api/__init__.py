#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API核心模块
提供API相关功能的统一入口
"""

import logging
from flask import Flask, Blueprint

from .error_handler import (
    init_error_handler, register_blueprint_error_handlers,
    register_error_mapping, api_error_handler, error_handler
)
from .response_formatter import (
    init_response_formatter, format_api_response,
    api_response, response_formatter
)

logger = logging.getLogger(__name__)

def init_api_core(app, log_exceptions=True, include_traceback=False):
    """
    初始化API核心组件
    
    Args:
        app: Flask应用实例
        log_exceptions: 是否记录异常日志
        include_traceback: 是否在响应中包含堆栈跟踪信息（仅在DEBUG模式下生效）
    """
    logger.info("初始化API核心组件...")
    
    # 初始化错误处理器
    init_error_handler(app, log_exceptions, include_traceback)
    
    # 初始化响应格式化器
    init_response_formatter(app)
    
    logger.info("API核心组件初始化完成")

def register_api_blueprint(blueprint):
    """
    注册API蓝图，为其添加错误处理器
    
    Args:
        blueprint: Flask蓝图实例
        
    Returns:
        Blueprint: 注册后的蓝图
    """
    # 注册蓝图的错误处理器
    register_blueprint_error_handlers(blueprint)
    
    logger.info(f"已为蓝图 {blueprint.name} 注册API错误处理器")
    return blueprint

__all__ = [
    'init_api_core',
    'register_api_blueprint',
    'register_error_mapping',
    'api_error_handler',
    'api_response',
    'format_api_response',
    'error_handler',
    'response_formatter'
] 