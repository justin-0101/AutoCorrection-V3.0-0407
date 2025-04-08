"""
Flask 扩展模块
用于初始化和管理所有 Flask 扩展
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import logging
from threading import Lock

logger = logging.getLogger(__name__)

class SafeSQLAlchemy(SQLAlchemy):
    """线程安全的SQLAlchemy扩展"""
    _lock = Lock()
    _initialized = False
    
    def init_app(self, app):
        """线程安全的初始化方法"""
        with self._lock:
            if not self._initialized or app.config.get('TESTING', False):
                super().init_app(app)
                self._initialized = True
                logger.info(f"SQLAlchemy已初始化，应用名称: {app.name}")
            else:
                logger.debug(f"SQLAlchemy已经初始化，跳过重复初始化，应用名称: {app.name}")

# 初始化 SQLAlchemy
db = SafeSQLAlchemy()

# 初始化 LoginManager
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # 设置登录视图的端点
login_manager.login_message = '请先登录'  # 设置登录提示消息
login_manager.login_message_category = 'info'  # 设置消息分类

# 初始化 Flask-Migrate
migrate = Migrate()

# 添加user_loader回调函数 - 在模块级别定义
@login_manager.user_loader
def load_user(user_id):
    try:
        # 在函数内部导入User模型以避免循环导入
        from app.models.user import User
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"加载用户时出错 {user_id}: {e}")
        return None

def init_extensions(app, skip_db=False):
    """
    初始化所有 Flask 扩展
    
    Args:
        app: Flask应用实例
        skip_db: 是否跳过数据库初始化，默认为False
    """
    try:
        # 初始化 SQLAlchemy（如果需要）
        if not skip_db:
            db.init_app(app)
            # 初始化 Flask-Migrate
            migrate.init_app(app, db)
            logger.info("数据库扩展初始化成功")
        
        # 初始化 LoginManager
        login_manager.init_app(app)
        logger.info("登录管理器初始化成功")
        
        # 在这里可以添加其他扩展的初始化
        
        return app
    except Exception as e:
        logger.error(f"初始化扩展时出错: {e}")
        raise 