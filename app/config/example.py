#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置示例文件
包含系统所需的各种配置参数示例
"""

# 应用基本配置
APP_CONFIG = {
    # 应用名称
    'name': '作文批改系统',
    # 应用版本
    'version': '2.0.0',
    # 调试模式
    'debug': True,
    # 密钥
    'secret_key': 'your-secret-key-replace-this-in-production',
    # 允许的主机
    'allowed_hosts': ['localhost', '127.0.0.1'],
    # 静态文件目录
    'static_folder': 'static',
    # 模板目录
    'template_folder': 'templates',
    # 上传文件目录
    'upload_folder': 'uploads',
    # 允许的文件类型
    'allowed_extensions': {
        'text': ['txt', 'docx', 'pdf'],
        'image': ['jpg', 'jpeg', 'png']
    },
    # 最大上传文件大小（字节）
    'max_content_length': 16 * 1024 * 1024,  # 16MB
    # 作文长度限制
    'max_essay_length': 5000,  # 最大字符数
}

# 数据库配置
DB_CONFIG = {
    # 数据库类型: sqlite, mysql, postgresql
    'type': 'sqlite',
    # 数据库路径 (sqlite)
    'path': 'instance/essay_correction.db',
    # 数据库连接信息（mysql/postgresql）
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'password',
    'database': 'essay_correction',
    # 连接池配置
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
}

# AI服务配置
AI_CONFIG = {
    # 文本生成AI
    'text_generation': {
        # 使用的AI提供商: openai, qwen, local
        'provider': 'qwen',
        # OpenAI配置
        'openai': {
            'api_key': 'sk-your-openai-api-key',
            'api_base': 'https://api.openai.com/v1',
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 2000,
        },
        # 阿里云千问配置
        'qwen': {
            'api_key': 'sk-your-qwen-api-key',
            'api_base': 'https://dashscope.aliyuncs.com/api/v1',
            'model': 'qwen-max',
            'temperature': 0.7,
            'max_tokens': 2000,
        },
        # 本地模型配置
        'local': {
            'model_path': 'models/local_model',
            'device': 'cuda',
        },
    },
    # 图像识别AI
    'image_recognition': {
        # 使用的AI提供商: qwen, azure, local
        'provider': 'qwen',
        # 阿里云千问配置
        'qwen': {
            'api_key': 'sk-your-qwen-api-key',
            'api_base': 'https://dashscope.aliyuncs.com/api/v1/services/vision/text/recognize',
            'model': 'qwen-vl-plus',
        },
        # Azure配置
        'azure': {
            'endpoint': 'https://your-resource.cognitiveservices.azure.com/',
            'api_key': 'your-azure-api-key',
        },
        # 本地模型配置
        'local': {
            'model_path': 'models/ocr_model',
            'device': 'cuda',
        },
    },
    # 批改模型配置
    'correction': {
        # 批改模型类型: rule_based, ai_based, hybrid
        'type': 'hybrid',
        # 评分权重
        'score_weights': {
            'content': 0.4,
            'organization': 0.2,
            'language': 0.3,
            'convention': 0.1,
        },
        # 批改提示词模板
        'prompt_template': 'templates/correction_prompt.txt',
    },
}

# 邮件服务配置
MAIL_CONFIG = {
    # SMTP服务器配置
    'smtp_server': 'smtp.example.com',
    'smtp_port': 587,
    'use_tls': True,
    'username': 'noreply@example.com',
    'password': 'your-email-password',
    # 发件人显示名
    'sender_name': '作文批改系统',
    # 发件人邮箱
    'sender_email': 'noreply@example.com',
    # 邮件主题前缀
    'subject_prefix': '[作文批改系统] ',
    # 邮件模板目录
    'template_dir': 'templates/email',
}

# 会员计划配置
MEMBERSHIP_CONFIG = {
    # 免费用户
    'free': {
        'name': '免费用户',
        'price': 0,
        'features': ['基础批改功能', '每日3篇作文', '每月10篇作文'],
        'daily_limit': 3,
        'monthly_limit': 10,
    },
    # 基础会员
    'basic': {
        'name': '基础会员',
        'price': 19.9,
        'features': ['标准批改功能', '每日10篇作文', '每月50篇作文', '历史数据分析'],
        'daily_limit': 10,
        'monthly_limit': 50,
    },
    # 高级会员
    'premium': {
        'name': '高级会员',
        'price': 39.9,
        'features': ['高级批改功能', '无限每日作文', '每月200篇作文', '详细报告和建议', '优先批改'],
        'daily_limit': 100,
        'monthly_limit': 200,
    },
}

# 安全配置
SECURITY_CONFIG = {
    # JWT令牌
    'jwt': {
        'secret_key': 'your-jwt-secret-key-change-in-production',
        'token_expires': 3600 * 24,  # 24小时
        'refresh_expires': 3600 * 24 * 7,  # 7天
        'algorithm': 'HS256',
    },
    # 密码策略
    'password_policy': {
        'min_length': 8,
        'require_upper': True,
        'require_lower': True,
        'require_digit': True,
        'require_special': False,
    },
    # CORS配置
    'cors': {
        'allowed_origins': ['http://localhost:3000', 'https://example.com'],
        'allowed_methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'allowed_headers': ['Content-Type', 'Authorization'],
        'expose_headers': ['Content-Length'],
        'supports_credentials': True,
    },
    # 验证码配置
    'captcha': {
        'enabled': True,
        'length': 6,
        'expires': 300,  # 5分钟
    },
}

# 备份配置
BACKUP_CONFIG = {
    # 备份目录
    'backup_dir': 'backups',
    # 报表目录
    'reports_dir': 'reports',
    # 保留的备份数量
    'daily_backups_to_keep': 7,   # 保留7天的每日备份
    'weekly_backups_to_keep': 4,  # 保留4周的每周备份
    'monthly_backups_to_keep': 12, # 保留12个月的每月备份
    # 备份时间
    'backup_time': '02:00',  # 凌晨2点
    # 是否启用自动备份
    'auto_backup': True,
}

# 管理员配置
ADMIN_CONFIG = {
    # 管理员邮箱列表
    'admin_emails': ['admin@example.com'],
    # 管理员角色
    'roles': {
        'admin': {
            'name': '管理员',
            'permissions': ['all'],
        },
        'moderator': {
            'name': '审核员',
            'permissions': ['read_all', 'edit_essays', 'view_reports'],
        },
    },
}

# Celery任务队列配置
CELERY_CONFIG = {
    # 消息代理配置
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    # Worker配置
    'worker_concurrency': 4,  # worker进程数
    'worker_max_tasks_per_child': 200,  # worker子进程在自动重启前最多执行的任务数
    # 任务超时设置
    'task_time_limit': 3600,  # 任务执行时间上限(秒)
    'task_soft_time_limit': 3000,  # 软超时(秒)
    # Flower监控配置
    'flower_port': 5555,
    'flower_basic_auth': ['admin:password'],
    # 任务序列化格式
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    # 任务队列权重
    'queue_priorities': {
        'high': 10,
        'default': 5,
        'low': 1,
    },
    # 任务发送重试配置
    'task_publish_retry': True,
    'max_retries': 3,
    # 定时任务配置
    'beat_schedule_filename': 'celerybeat-schedule',
    # 是否启用任务结果后端
    'task_ignore_result': False,
    # 任务结果过期时间
    'result_expires': 3600,  # 1小时
}

# 日志配置
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'detailed',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        },
        'error_file': {
            'level': 'ERROR',
            'formatter': 'detailed',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'app': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# 支付配置
PAYMENT_CONFIG = {
    "alipay": {
        "enabled": True,
        "app_id": "your-alipay-app-id",
        "app_private_key": "your-alipay-private-key",
        "alipay_public_key": "alipay-public-key",
        "notify_url": "https://yourdomain.com/api/v1/payment/callback/alipay",
        "return_url": "https://yourdomain.com/payment/result",
        "sandbox": True,  # 是否使用沙箱环境
    },
    "wechat": {
        "enabled": True,
        "app_id": "your-wechat-app-id",
        "mch_id": "your-wechat-mch-id",
        "api_key": "your-wechat-api-key",
        "cert_path": "path/to/wechat/cert.pem",
        "key_path": "path/to/wechat/key.pem",
        "notify_url": "https://yourdomain.com/api/v1/payment/callback/wechat",
        "sandbox": True,  # 是否使用沙箱环境
    },
    "currency": "CNY",  # 默认货币
    "auto_activate": True,  # 支付成功后自动激活会员
    "payment_timeout": 3600,  # 支付超时时间(秒)
    "retry_times": 3,  # 支付重试次数
}
