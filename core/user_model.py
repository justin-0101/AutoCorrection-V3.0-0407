from datetime import datetime, timedelta
import hashlib
import secrets
import logging
from app.modules.utils.db_manager import db_manager
from app.modules.utils.exceptions import DatabaseError, ValidationError, db_error_handler
from config.app_config import USER_CONFIG

logger = logging.getLogger('autocorrection.user')

class User:
    """用户模型类，处理用户相关的数据库操作和业务逻辑"""
    
    def __init__(self, id=None, username=None, email=None, password_hash=None, 
                 user_type='free', created_at=None, last_login=None, token=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.user_type = user_type  # free, regular, premium
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
        self.token = token
    
    @staticmethod
    def hash_password(password):
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def generate_token():
        """生成用户令牌"""
        return secrets.token_hex(32)
    
    @db_error_handler
    def save(self):
        """保存用户到数据库（新建或更新）"""
        if self.id:
            # 更新现有用户
            query = """
                UPDATE users 
                SET username=?, email=?, password_hash=?, user_type=?, last_login=?, token=?
                WHERE id=?
            """
            params = (self.username, self.email, self.password_hash, self.user_type, 
                      self.last_login, self.token, self.id)
            db_manager.execute_query(query, params)
            logger.info(f"已更新用户 ID: {self.id}")
            return self.id
        else:
            # 创建新用户
            query = """
                INSERT INTO users (username, email, password_hash, user_type, created_at, last_login, token)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (self.username, self.email, self.password_hash, self.user_type, 
                      self.created_at, self.last_login, self.token)
            self.id = db_manager.execute_query(query, params)
            logger.info(f"已创建新用户 ID: {self.id}")
            return self.id
    
    @staticmethod
    @db_error_handler
    def find_by_id(user_id):
        """通过ID查找用户"""
        query = "SELECT * FROM users WHERE id = ?"
        user_data = db_manager.execute_query(query, (user_id,), fetch_one=True)
        if not user_data:
            return None
        return User(**user_data)
    
    @staticmethod
    @db_error_handler
    def find_by_email(email):
        """通过邮箱查找用户"""
        query = "SELECT * FROM users WHERE email = ?"
        user_data = db_manager.execute_query(query, (email,), fetch_one=True)
        if not user_data:
            return None
        return User(**user_data)
    
    @staticmethod
    @db_error_handler
    def find_by_token(token):
        """通过令牌查找用户"""
        query = "SELECT * FROM users WHERE token = ?"
        user_data = db_manager.execute_query(query, (token,), fetch_one=True)
        if not user_data:
            return None
        return User(**user_data)
    
    @staticmethod
    @db_error_handler
    def authenticate(email, password):
        """验证用户凭据"""
        password_hash = User.hash_password(password)
        user = User.find_by_email(email)
        
        if not user or user.password_hash != password_hash:
            logger.warning(f"登录失败: {email}")
            return None
        
        # 更新登录时间和生成新令牌
        user.last_login = datetime.now()
        user.token = User.generate_token()
        user.save()
        
        logger.info(f"用户登录成功: {user.id}")
        return user
    
    @db_error_handler
    def check_essay_limit(self):
        """检查用户作文数量是否超出限制"""
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        # 获取今日作文数
        daily_query = """
            SELECT COUNT(*) as count FROM essays 
            WHERE user_id = ? AND DATE(created_at) = DATE(?)
        """
        daily_result = db_manager.execute_query(daily_query, (self.id, today), fetch_one=True)
        daily_count = daily_result['count'] if daily_result else 0
        
        # 获取本月作文数
        monthly_query = """
            SELECT COUNT(*) as count FROM essays 
            WHERE user_id = ? AND DATE(created_at) >= DATE(?)
        """
        monthly_result = db_manager.execute_query(monthly_query, (self.id, month_start), fetch_one=True)
        monthly_count = monthly_result['count'] if monthly_result else 0
        
        # 根据用户类型判断限额
        if self.user_type == 'free':
            if monthly_count >= USER_CONFIG['FREE_ESSAYS_LIMIT']:
                return False, f"免费用户每月限制 {USER_CONFIG['FREE_ESSAYS_LIMIT']} 篇作文"
        elif self.user_type == 'regular':
            if daily_count >= USER_CONFIG['REGULAR_DAILY_ESSAYS']:
                return False, f"普通用户每日限制 {USER_CONFIG['REGULAR_DAILY_ESSAYS']} 篇作文"
            if monthly_count >= USER_CONFIG['REGULAR_MONTHLY_ESSAYS']:
                return False, f"普通用户每月限制 {USER_CONFIG['REGULAR_MONTHLY_ESSAYS']} 篇作文"
        elif self.user_type == 'premium':
            if daily_count >= USER_CONFIG['PREMIUM_DAILY_ESSAYS']:
                return False, f"高级用户每日限制 {USER_CONFIG['PREMIUM_DAILY_ESSAYS']} 篇作文"
            if monthly_count >= USER_CONFIG['PREMIUM_MONTHLY_ESSAYS']:
                return False, f"高级用户每月限制 {USER_CONFIG['PREMIUM_MONTHLY_ESSAYS']} 篇作文"
        
        return True, ""
    
    @staticmethod
    @db_error_handler
    def register(username, email, password):
        """注册新用户"""
        # 检查邮箱是否已存在
        if User.find_by_email(email):
            raise ValidationError("邮箱已被注册")
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            password_hash=User.hash_password(password),
            token=User.generate_token(),
            created_at=datetime.now(),
            last_login=datetime.now()
        )
        user.save()
        logger.info(f"新用户注册: {user.id}")
        return user 