"""
数据库连接管理器
提供统一的数据库访问接口
"""

import sqlite3
import threading
import logging
import os
from flask_sqlalchemy import SQLAlchemy
from contextlib import contextmanager
from app.extensions import db

# 获取logger
logger = logging.getLogger(__name__)

class DBManager:
    """数据库连接管理器，单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DBManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, app=None, db_path=None):
        """初始化数据库管理器
        
        Args:
            app: Flask应用实例
            db_path: 数据库路径
        """
        if self._initialized:
            return
            
        self.app = app
        self._db = None
        self.db_path = db_path or 'instance/essay_correction.db'
        self._local = threading.local()
        self._initialized = True
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化与Flask应用的集成
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', f'sqlite:///{self.db_path}')
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
        
        db.init_app(app)
        
        # 确保实例目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @property
    def db(self):
        """获取SQLAlchemy实例"""
        if self._db is None:
            self._db = db
        return self._db
    
    def create_all(self):
        """创建所有表"""
        if self._db is not None:
            with self.app.app_context():
                self._db.create_all()
                logger.info("数据库表已创建")
    
    def get_connection(self):
        """获取数据库连接，用于原生SQL查询
        
        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
            logger.debug(f"创建新的数据库连接: {id(self._local.connection)}")
        return self._local.connection
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
            logger.debug("关闭数据库连接")
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器
        
        Yields:
            sqlite3.Cursor: 数据库游标对象
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作异常: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, query, params=None):
        """执行查询语句
        
        Args:
            query (str): SQL查询
            params (tuple, optional): 查询参数
            
        Returns:
            list: 查询结果
        """
        params = params or ()
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query, params=None):
        """执行更新语句
        
        Args:
            query (str): SQL更新语句
            params (tuple, optional): 更新参数
            
        Returns:
            int: 受影响的行数
        """
        params = params or ()
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器
        
        用法:
        with db_manager.transaction() as cursor:
            cursor.execute("INSERT INTO users VALUES (?)", ('user1',))
            cursor.execute("INSERT INTO profiles VALUES (?)", ('profile1',))
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
            logger.debug("事务提交成功")
        except Exception as e:
            conn.rollback()
            logger.error(f"事务回滚: {str(e)}")
            raise
        finally:
            cursor.close()


# 创建全局数据库管理器实例
db_manager = DBManager()
