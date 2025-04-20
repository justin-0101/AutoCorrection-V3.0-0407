#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
上下文处理器模块
提供给模板使用的上下文变量和函数
"""

import os
import datetime
from flask import current_app, url_for

def register_context_processors(app):
    """
    注册上下文处理器
    
    Args:
        app: Flask应用实例
    """
    @app.context_processor
    def inject_app_info():
        """注入应用信息到模板"""
        return {
            'app_name': '作文批改系统',
            'app_version': 'v3.0',
            'current_year': datetime.datetime.now().year
        }
    
    @app.context_processor
    def inject_debug_info():
        """注入调试信息到模板"""
        return {
            'debug': app.debug,
            'testing': app.testing
        }
    
    @app.context_processor
    def utility_processor():
        """注入实用函数到模板"""
        def format_datetime(dt, format='%Y-%m-%d %H:%M'):
            """格式化日期时间"""
            if dt is None:
                return ''
            if isinstance(dt, (int, float)):
                dt = datetime.datetime.fromtimestamp(dt)
            return dt.strftime(format)
        
        def get_static_url(filename):
            """获取静态文件URL"""
            return url_for('static', filename=filename)
        
        return {
            'format_datetime': format_datetime,
            'get_static_url': get_static_url
        }
    
    app.logger.info('上下文处理器已注册') 