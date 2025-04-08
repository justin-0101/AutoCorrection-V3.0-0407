"""
初始化数据库结构迁移脚本
"""

import logging
from database.db_manager import db_manager

logger = logging.getLogger(__name__)

def upgrade():
    """升级数据库结构"""
    with db_manager.get_cursor() as cursor:
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            role TEXT DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        logger.info("创建或更新用户表")
        
        # 创建用户资料表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT,
            school TEXT,
            grade TEXT,
            avatar_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        logger.info("创建或更新用户资料表")
        
        # 创建验证码表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            purpose TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_used BOOLEAN DEFAULT 0
        )
        ''')
        logger.info("创建或更新验证码表")
        
        # 创建登录历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        logger.info("创建或更新登录历史表")
        
        # 创建作文表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS essays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT,
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            word_count INTEGER,
            total_score INTEGER,
            grade TEXT,
            content_score INTEGER,
            language_score INTEGER,
            structure_score INTEGER,
            writing_score INTEGER,
            spelling_errors TEXT,
            overall_assessment TEXT,
            content_analysis TEXT,
            language_analysis TEXT,
            structure_analysis TEXT,
            writing_analysis TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        logger.info("创建或更新作文表")
        
        # 创建网站配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS website_config (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name TEXT UNIQUE NOT NULL,
            config_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        logger.info("创建或更新网站配置表")
        
        # 添加基本配置
        configs = [
            ('site_title', '小园丁作文批改智能体'),
            ('site_description', '智能作文批改系统'),
            ('free_user_quota', '10'),
            ('regular_user_monthly_quota', '300'),
            ('premium_user_monthly_quota', '500'),
            ('regular_user_daily_limit', '30'),
            ('premium_user_daily_limit', '60'),
            ('last_backup_time', '从未备份')
        ]
        
        # 检查是否已存在配置，不存在则添加
        for name, value in configs:
            cursor.execute("SELECT COUNT(*) FROM website_config WHERE config_name = ?", (name,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO website_config (config_name, config_value) VALUES (?, ?)",
                    (name, value)
                )
        
        logger.info("基本配置添加成功")
        
        # 创建会员等级表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            membership_type TEXT DEFAULT 'free',
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            payment_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        logger.info("创建或更新会员等级表")
        
        # 创建支付历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT,
            transaction_id TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        logger.info("创建或更新支付历史表")

def downgrade():
    """回滚数据库结构（危险操作，谨慎使用）"""
    with db_manager.get_cursor() as cursor:
        # 按照依赖关系的反序删除表
        tables = [
            "payment_history",
            "memberships",
            "essays",
            "login_history",
            "verification_codes",
            "user_profiles",
            "users",
            "website_config"
        ]
        
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            logger.warning(f"删除表: {table}")
            
    logger.warning("所有表已删除") 