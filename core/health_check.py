import sqlite3
import os
import logging
from flask import jsonify
from config.app_config import APP_CONFIG

logger = logging.getLogger('autocorrection.health')

def health_check():
    """系统健康检查"""
    status = {
        "status": "ok",
        "components": {
            "database": check_database(),
            "ai_service": check_ai_service(),
            "storage": check_storage()
        }
    }
    
    # 如果任何组件状态不为ok，整体状态为error
    if any(v != "ok" for v in status["components"].values()):
        status["status"] = "error"
    
    return jsonify(status)

def check_database():
    """检查数据库连接"""
    try:
        conn = sqlite3.connect(APP_CONFIG['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        return "ok"
    except Exception as e:
        logger.error(f"数据库健康检查失败: {str(e)}")
        return f"error: {str(e)}"

def check_ai_service():
    """检查AI服务状态"""
    if not os.environ.get('DEEPSEEK_API_KEY'):
        return "error: API密钥未配置"
    return "ok"

def check_storage():
    """检查存储目录"""
    upload_dir = APP_CONFIG['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        try:
            os.makedirs(upload_dir)
            return "ok"
        except Exception as e:
            return f"error: 无法创建上传目录 - {str(e)}"
    
    # 检查目录是否可写
    try:
        test_file = os.path.join(upload_dir, 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return "ok"
    except Exception as e:
        return f"error: 目录不可写 - {str(e)}" 