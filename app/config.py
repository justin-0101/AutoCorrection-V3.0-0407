#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
应用配置文件
包含基础配置、开发配置、生产配置等
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '../.env')) # 假设.env在项目根目录

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_hard_to_guess_string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/essay_correction.db'
    
    # 使用绝对路径
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'essay_correction.db'))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{DB_PATH}'
    
    # JWT 配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'another_hard_to_guess_string'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 24 * 3600 # 30 days
    
    # Celery 配置
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'docx', 'doc'}
    
    # DeepSeek API 配置
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    
    # 会员配置
    MEMBERSHIP_CONFIG = {
        # 会员计划定义
        'plans': [
            {
                'id': 'monthly',
                'name': '月度会员',
                'price': 39.9,
                'duration_days': 30,
                'daily_limit': 5,
                'features': ['无限作文批改', '作文评分', '详细改进建议', '高级语法修正']
            },
            {
                'id': 'yearly',
                'name': '年度会员',
                'price': 365.0,
                'duration_days': 365,
                'daily_limit': 10,
                'features': ['无限作文批改', '作文评分', '详细改进建议', '高级语法修正', '词汇提升建议', '专家点评']
            },
            {
                'id': 'lifetime',
                'name': '终身会员',
                'price': 998.0,
                'duration_days': 36500,  # 100年 = 终身
                'daily_limit': 20,
                'features': ['无限作文批改', '作文评分', '详细改进建议', '高级语法修正', '词汇提升建议', '专家点评', '一对一咨询']
            }
        ],
        
        # 免费用户限制
        'free_limits': {
            'daily': 1,
            'monthly': 5,
            'max_essays': 10
        },
        
        # 不同等级会员的作文批改限制
        'essay_limits': {
            'free': {'daily': 1, 'monthly': 5},
            'basic': {'daily': 5, 'monthly': 30},
            'premium': {'daily': 10, 'monthly': 100},
            'lifetime': {'daily': 20, 'monthly': -1}  # -1表示无限制
        },
        
        # 支付相关配置
        'payment': {
            'expiry_reminder_days': [7, 3, 1],  # 到期前几天发送提醒
            'grace_period_days': 3,  # 到期后的宽限期(天)
            'retry_payment_times': 3  # 支付失败重试次数
        }
    }
    
    # 应用通用配置
    APP_CONFIG = {
        'max_essay_length': 5000,  # 最大作文长度(字符)
        'allowed_extensions': {
            'text': ['txt', 'docx', 'pdf'],
            'image': ['jpg', 'jpeg', 'png']
        },
        'temp_dir': 'temp',
        'upload_dir': 'uploads'
    }

    # 支付配置
    PAYMENT_CONFIG = {
        'currency': 'CNY',
        'payment_methods': ['wechat', 'alipay', 'credit_card'],
        'expiry_reminder_days': [7, 3, 1],  # 到期前几天发送提醒
        'grace_period_days': 3,  # 到期后宽限期
        'auto_renewal': True,
        'providers': {
            'wechat': {
                'app_id': os.environ.get('WECHAT_APP_ID'),
                'mch_id': os.environ.get('WECHAT_MCH_ID'),
                'api_key': os.environ.get('WECHAT_API_KEY')
            },
            'alipay': {
                'app_id': os.environ.get('ALIPAY_APP_ID'),
                'private_key': os.environ.get('ALIPAY_PRIVATE_KEY'),
                'public_key': os.environ.get('ALIPAY_PUBLIC_KEY')
            }
        }
    }

    # 邮件配置
    MAIL_CONFIG = {
        'MAIL_SERVER': os.environ.get('MAIL_SERVER', 'smtp.example.com'),
        'MAIL_PORT': int(os.environ.get('MAIL_PORT', 587)),
        'MAIL_USERNAME': os.environ.get('MAIL_USERNAME', 'user@example.com'),
        'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD', 'password'),
        'MAIL_USE_TLS': bool(os.environ.get('MAIL_USE_TLS', True)),
        'MAIL_USE_SSL': bool(os.environ.get('MAIL_USE_SSL', False)),
        'MAIL_DEFAULT_SENDER': os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@autocorrection.com'),
        'MAIL_SUBJECT_PREFIX': '[AutoCorrection] ',
        'MAIL_TEMPLATES': {
            'welcome': 'emails/welcome.html',
            'reset_password': 'emails/reset_password.html',
            'subscription_expiry': 'emails/subscription_expiry.html',
            'payment_success': 'emails/payment_success.html',
            'payment_failed': 'emails/payment_failed.html'
        }
    }

    # 备份配置
    BACKUP_CONFIG = {
        'backup_dir': os.path.abspath(os.path.join(os.path.dirname(__file__), '../backups')),
        'max_backups': 10,
        'backup_interval': 24,  # 小时
        'compression': True,
        'include_uploads': True,
        'backup_filename_template': 'backup_%Y%m%d_%H%M%S.zip',
        'auto_backup_enabled': True,
        'notification_enabled': True,
        'notification_emails': ['admin@autocorrection.com']
    }
    
    # 数据库配置
    DB_CONFIG = {
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_RECORD_QUERIES': True,
        'SQLALCHEMY_ECHO': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        },
        'db_type': 'postgresql',
        'db_name': os.environ.get('DB_NAME', 'autocorrection'),
        'db_user': os.environ.get('DB_USER', 'postgres'),
        'db_password': os.environ.get('DB_PASSWORD', 'password'),
        'db_host': os.environ.get('DB_HOST', 'localhost'),
        'db_port': os.environ.get('DB_PORT', '5432')
    }
    
    # 管理员配置
    ADMIN_CONFIG = {
        'admin_emails': [
            os.environ.get('ADMIN_EMAIL', 'admin@autocorrection.com'),
            os.environ.get('SUPPORT_EMAIL', 'support@autocorrection.com')
        ],
        'admin_roles': ['admin', 'super_admin'],
        'admin_permissions': {
            'admin': [
                'view_users',
                'manage_users',
                'view_essays',
                'manage_essays',
                'view_reports',
                'manage_memberships'
            ],
            'super_admin': [
                'view_users',
                'manage_users',
                'view_essays',
                'manage_essays',
                'view_reports',
                'manage_memberships',
                'manage_system',
                'manage_admins'
            ]
        },
        'admin_dashboard': {
            'default_view': 'overview',
            'refresh_interval': 300,  # 5分钟
            'charts_enabled': True,
            'export_formats': ['csv', 'excel', 'pdf']
        },
        'notification_settings': {
            'email_notifications': True,
            'system_notifications': True,
            'alert_thresholds': {
                'user_registration': 100,  # 每日新用户注册超过100发送提醒
                'essay_submission': 1000,  # 每日作文提交超过1000发送提醒
                'error_rate': 0.05,  # 错误率超过5%发送提醒
                'system_load': 0.8   # 系统负载超过80%发送提醒
            }
        }
    }

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
    # Celery配置
    CELERY_CONFIG = {
        'broker_url': 'redis://localhost:6379/0',
        'result_backend': 'redis://localhost:6379/1',
        'task_serializer': 'json',
        'result_serializer': 'json',
        'accept_content': ['json'],
        'timezone': 'Asia/Shanghai',
        'enable_utc': True,
        'task_acks_late': True,
        'task_reject_on_worker_lost': True,
        'task_track_started': True,
        'worker_prefetch_multiplier': 1,
        'worker_max_tasks_per_child': 500,
        'result_expires': 60 * 60 * 24,  # 1天
        'task_default_queue': 'default',
        'task_default_exchange': 'default',
        'task_default_routing_key': 'default',
        'task_routes': {
            'tasks.correction_tasks.*': {'queue': 'corrections'},
            'tasks.user_tasks.*': {'queue': 'users'},
        }
    }
    
    # 应用配置
    APP_CONFIG = {
        'name': 'AutoCorrection',
        'version': '2.0.0',
        'debug': True,
        'log_level': 'DEBUG',
        'secret_key': os.getenv('SECRET_KEY', 'dev-secret-key'),
        'allowed_extensions': ['txt', 'doc', 'docx', 'pdf'],
        'upload_folder': os.path.join(basedir, 'uploads'),
        'max_content_length': 16 * 1024 * 1024,  # 16MB
    }
    
    # 数据库配置
    DB_CONFIG = {
        'SQLALCHEMY_DATABASE_URI': os.getenv(
            'DATABASE_URL',
            f"sqlite:///{os.path.join(basedir, 'autocorrection.db')}"
        ),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_RECORD_QUERIES': True,
        'db_name': os.getenv('DB_NAME', 'autocorrection'),
        'db_user': os.getenv('DB_USER', 'root'),
        'db_password': os.getenv('DB_PASSWORD', ''),
        'db_host': os.getenv('DB_HOST', 'localhost'),
        'db_port': int(os.getenv('DB_PORT', 3306))
    }
    
    # 邮件配置
    MAIL_CONFIG = {
        'MAIL_SERVER': os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        'MAIL_PORT': int(os.getenv('MAIL_PORT', 587)),
        'MAIL_USE_TLS': True,
        'MAIL_USERNAME': os.getenv('MAIL_USERNAME'),
        'MAIL_PASSWORD': os.getenv('MAIL_PASSWORD'),
        'MAIL_DEFAULT_SENDER': os.getenv('MAIL_DEFAULT_SENDER', 'noreply@autocorrection.com')
    }
    
    # 支付配置
    PAYMENT_CONFIG = {
        'stripe_public_key': os.getenv('STRIPE_PUBLIC_KEY'),
        'stripe_secret_key': os.getenv('STRIPE_SECRET_KEY'),
        'stripe_webhook_secret': os.getenv('STRIPE_WEBHOOK_SECRET'),
        'currency': 'usd',
        'payment_methods': ['card'],
        'subscription_plans': {
            'basic': {
                'name': 'Basic Plan',
                'price_id': os.getenv('STRIPE_BASIC_PRICE_ID'),
                'features': ['基础批改', '每月10篇文章']
            },
            'premium': {
                'name': 'Premium Plan',
                'price_id': os.getenv('STRIPE_PREMIUM_PRICE_ID'),
                'features': ['高级批改', '每月30篇文章', '优先处理']
            },
            'professional': {
                'name': 'Professional Plan',
                'price_id': os.getenv('STRIPE_PRO_PRICE_ID'),
                'features': ['专业批改', '无限文章', '24/7支持']
            }
        }
    }
    
    # 备份配置
    BACKUP_CONFIG = {
        'backup_dir': os.path.join(basedir, 'backups'),
        'max_backups': 10,
        'backup_interval': 24,  # 小时
        'compression': True,
        'notify_on_success': True,
        'notify_on_failure': True,
        'backup_types': ['database', 'uploads', 'logs']
    }
    
    # AI 配置
    AI_CONFIG = {
        'model': 'gpt-4',
        'api_key': os.getenv('OPENAI_API_KEY'),
        'text_api_url': os.getenv('AI_TEXT_API_URL', 'https://api.openai.com/v1/chat/completions'),
        'max_tokens': 2000,
        'temperature': 0.7,
        'timeout': 30,  # 秒
        'retry_attempts': 3,
        'retry_delay': 1,  # 秒
        'batch_size': 5,
        'concurrent_requests': 3,
        'cache_results': True,
        'cache_ttl': 3600,  # 秒
        'prompt_templates': {
            'correction': 'Please correct the following essay:\n{text}',
            'feedback': 'Please provide feedback for the following essay:\n{text}',
            'scoring': 'Please score the following essay based on these criteria:\n{criteria}\n\nEssay:\n{text}'
        },
        'scoring_criteria': {
            'content': '内容完整性、逻辑性和创意',
            'language': '语言准确性、词汇丰富度和语法正确性',
            'structure': '文章结构、段落组织和衔接',
            'style': '写作风格、表达技巧和修辞手法'
        },
        'feedback_aspects': [
            '内容分析',
            '语言表达',
            '结构组织',
            '创意思维',
            '改进建议'
        ]
    }
    
    # 会员配置
    MEMBERSHIP_CONFIG = {
        # 会员计划定义
        'plans': [
            {
                'id': 'monthly',
                'name': '月度会员',
                'price': 39.9,
                'duration_days': 30,
                'daily_limit': 5,
                'features': ['无限作文批改', '作文评分', '详细改进建议', '高级语法修正']
            },
            {
                'id': 'yearly',
                'name': '年度会员',
                'price': 365.0,
                'duration_days': 365,
                'daily_limit': 10,
                'features': ['无限作文批改', '作文评分', '详细改进建议', '高级语法修正', '词汇提升建议', '专家点评']
            },
            {
                'id': 'lifetime',
                'name': '终身会员',
                'price': 998.0,
                'duration_days': 36500,  # 100年 = 终身
                'daily_limit': 20,
                'features': ['无限作文批改', '作文评分', '详细改进建议', '高级语法修正', '词汇提升建议', '专家点评', '一对一咨询']
            }
        ],
        
        # 免费用户限制
        'free_limits': {
            'daily': 1,
            'monthly': 5,
            'max_essays': 10
        },
        
        # 不同等级会员的作文批改限制
        'essay_limits': {
            'free': {'daily': 1, 'monthly': 5},
            'basic': {'daily': 5, 'monthly': 30},
            'premium': {'daily': 10, 'monthly': 100},
            'lifetime': {'daily': 20, 'monthly': -1}  # -1表示无限制
        },
        
        # 支付相关配置
        'payment': {
            'expiry_reminder_days': [7, 3, 1],  # 到期前几天发送提醒
            'grace_period_days': 3,  # 到期后的宽限期(天)
            'retry_payment_times': 3  # 支付失败重试次数
        }
    }
    
    # 管理员配置
    ADMIN_CONFIG = {
        'admin_emails': [
            os.getenv('ADMIN_EMAIL', 'admin@autocorrection.com'),
            os.getenv('SUPPORT_EMAIL', 'support@autocorrection.com')
        ],
        'admin_roles': ['admin', 'super_admin'],
        'admin_permissions': {
            'admin': [
                'view_users',
                'manage_users',
                'view_essays',
                'manage_essays',
                'view_reports',
                'manage_memberships'
            ],
            'super_admin': [
                'view_users',
                'manage_users',
                'view_essays',
                'manage_essays',
                'view_reports',
                'manage_memberships',
                'manage_system',
                'manage_settings'
            ]
        },
        'dashboard_config': {
            'refresh_interval': 300,  # 5分钟
            'stats_cache_ttl': 3600,  # 1小时
            'default_view': 'overview'
        },
        'notification_settings': {
            'notify_on_user_register': True,
            'notify_on_payment_failure': True,
            'notify_on_system_error': True
        }
    }

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False # 测试时通常禁用CSRF保护
    
    # Celery同步执行配置
    CELERY_TASK_ALWAYS_EAGER = True  # 测试环境下同步执行任务
    CELERY_TASK_EAGER_PROPAGATES = True  # 同步模式下传播异常

class ProductionConfig(Config):
    """生产环境配置"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
    # 生产环境的其他配置，例如日志级别、服务器设置等

# 配置字典，用于根据名称加载配置
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    'default': DevelopmentConfig # 默认使用开发配置
}

# 使用方案二：创建一个字典访问包装器类
class ConfigWrapper(dict):
    """配置包装器，同时支持字典访问和属性访问"""
    def __init__(self, config_dict):
        super().__init__(config_dict)
        # 将配置类的实例作为属性
        self.instance = DevelopmentConfig()
    
    def __getattr__(self, name):
        # 尝试从配置实例获取属性
        return getattr(self.instance, name)

# 用包装器替换原始 config 字典，使其在导入时可用
config = ConfigWrapper(config)

# 定义加载配置的函数
def load_config(config_name):
    """
    根据配置名称加载配置类
    
    Args:
        config_name (str): 配置名称 ('development', 'testing', 'production')
        
    Returns:
        Config: 对应的配置类实例
    """
    return config.get(config_name, config['default'])

# 创建一个默认的配置实例，供直接导入使用
# 这是为了兼容直接使用 from app.config import config 语法的代码
default_config = DevelopmentConfig()

# 在 config 字典上添加必要的属性，以便通过 config.attr 语法访问
for attr_name in dir(default_config):
    if not attr_name.startswith('_'):  # 忽略私有属性
        setattr(config, attr_name, getattr(default_config, attr_name)) 