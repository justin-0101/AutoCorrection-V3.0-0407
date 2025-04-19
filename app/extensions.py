"""
Flask 扩展模块
用于初始化和管理所有 Flask 扩展
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import logging
import os

logger = logging.getLogger(__name__)

# 检查是否使用eventlet
is_using_eventlet = os.environ.get('CELERY_WORKER_POOL', '').lower() == 'eventlet'

# 全局配置
if is_using_eventlet:
    # 当使用eventlet时，完全禁用连接池，使用NullPool避免并发问题
    from sqlalchemy.pool import NullPool
    engine_options = {
        'poolclass': NullPool,
    }
    db = SQLAlchemy(engine_options=engine_options)
    logger.info("检测到Eventlet环境，使用NullPool（无连接池）配置")
    
    # 修补SQLAlchemy的互斥锁，避免循环导入
    try:
        import sqlalchemy.util.queue
        original_notify = sqlalchemy.util.queue.Queue.notify
        
        # 定义安全的notify方法
        def safe_notify(self):
            if not hasattr(self, 'mutex') or not self.mutex.locked():
                return
            return original_notify(self)
            
        # 应用补丁
        sqlalchemy.util.queue.Queue.notify = safe_notify
        logger.info("已修补SQLAlchemy Queue.notify方法")
    except Exception as e:
        logger.error(f"修补SQLAlchemy时出错: {str(e)}")
else:
    # 正常模式下使用标准配置，但启用连接池健康检查
    db = SQLAlchemy(engine_options={
        'pool_pre_ping': True,
        'pool_recycle': 3600,  # 1小时后回收连接
    })
    logger.info("使用标准SQLAlchemy连接池配置")

# 初始化 LoginManager
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # 设置登录视图的端点
login_manager.login_message = '请先登录'  # 设置登录提示消息
login_manager.login_message_category = 'info'  # 设置消息分类

# 初始化 Flask-Migrate
migrate = Migrate()

# 初始化 CSRFProtect
csrf = CSRFProtect()

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
            # 检查数据库配置
            if is_using_eventlet:
                logger.warning("在Eventlet环境中禁用了SQLAlchemy连接池，使用NullPool")
                # 确保app配置反映这一点
                app.config['SQLALCHEMY_POOL_SIZE'] = None
                app.config['SQLALCHEMY_POOL_TIMEOUT'] = None
                app.config['SQLALCHEMY_POOL_RECYCLE'] = None
                
            db.init_app(app)
            # 初始化 Flask-Migrate
            migrate.init_app(app, db)
            logger.info("数据库扩展初始化成功")
        
        # 初始化 LoginManager
        login_manager.init_app(app)
        logger.info("登录管理器初始化成功")
        
        # 初始化 CSRFProtect
        csrf.init_app(app)
        logger.info("CSRF保护初始化成功")
        
        # 在这里可以添加其他扩展的初始化
        
        return app
    except Exception as e:
        logger.error(f"初始化扩展时出错: {e}")
        raise