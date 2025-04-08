"""
数据库模块
提供数据库连接和初始化功能
"""

import logging
from app.extensions import db, migrate

# 导出主要对象和函数
__all__ = ['db', 'migrate']

logger = logging.getLogger(__name__)

def init_app(app):
    """
    初始化数据库连接（已弃用，请使用app.extensions.init_extensions）
    
    Args:
        app: Flask应用实例
    """
    logger.warning("database.init_app已弃用，请使用app.extensions.init_extensions进行初始化")
    return db
