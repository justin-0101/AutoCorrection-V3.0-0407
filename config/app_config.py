import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 应用配置
APP_CONFIG = {
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'your_secret_key_here'),
    'SESSION_LIFETIME_DAYS': 30,
    'UPLOAD_FOLDER': 'uploads',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
    'DATABASE_PATH': 'instance/essay_correction.db'
}

# AI配置
AI_CONFIG = {
    'API_KEY': os.environ.get('DEEPSEEK_API_KEY', ''),
    'BASE_URL': os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
    'MODEL': os.environ.get('DEEPSEEK_MODEL', 'deepseek-reasoner'),
    'TEMPERATURE': 0.2,
    'MAX_TOKENS': 2000,
    'TIMEOUT': 100.0
}

# 用户配置
USER_CONFIG = {
    'FREE_ESSAYS_LIMIT': int(os.environ.get('FREE_ESSAYS_LIMIT', 10)),
    'REGULAR_MONTHLY_ESSAYS': int(os.environ.get('REGULAR_MONTHLY_ESSAYS', 300)),
    'REGULAR_DAILY_ESSAYS': int(os.environ.get('REGULAR_DAILY_ESSAYS', 30)),
    'PREMIUM_MONTHLY_ESSAYS': int(os.environ.get('PREMIUM_MONTHLY_ESSAYS', 500)),
    'PREMIUM_DAILY_ESSAYS': int(os.environ.get('PREMIUM_DAILY_ESSAYS', 60))
}

# 上传文件配置
UPLOAD_CONFIG = {
    'ALLOWED_EXTENSIONS': {'txt', 'pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif'},
    'MAX_FILE_SIZE': 5 * 1024 * 1024  # 5MB
} 