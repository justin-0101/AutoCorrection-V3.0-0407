#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工具包，提供各种通用工具功能
"""

# 使用懒加载方式导入 FileHandler 以避免循环导入问题
def get_file_handler():
    """获取文件处理器实例"""
    from app.utils.file_handler import FileHandler
    return FileHandler()

# 导出的符号
__all__ = ['get_file_handler'] 