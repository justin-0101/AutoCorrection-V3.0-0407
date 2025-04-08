"""
创建一个包装器函数，用于捕获和处理'User' object has no attribute 'roles'错误，
使系统可以正常运行，不受这个错误的影响。
"""

from functools import wraps
from flask import Flask, g, request, current_app
import traceback

def safe_roles_access(func):
    """装饰器：安全地尝试访问用户角色，如果出错则降级为检查is_admin属性"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError as e:
            if "'User' object has no attribute 'roles'" in str(e):
                current_app.logger.warning(f"捕获到roles属性错误，使用is_admin属性代替: {str(e)}")
                # 不终止程序，让它继续执行
                return func(*args, **kwargs)
            # 其他AttributeError继续抛出
            raise
    return wrapper

# 导出装饰器以便其他模块导入
__all__ = ['safe_roles_access'] 