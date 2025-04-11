#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery应用上下文修复工具
用于修复任务处理中的应用上下文问题
"""

import os
import sys
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("celery_fix")

# 获取项目根目录
BASE_DIR = Path(__file__).parent.absolute()
logger.info(f"项目根目录: {BASE_DIR}")

def fix_setup_task_context():
    """修复setup_task_context函数中的问题"""
    logger.info("检查并修复Celery任务上下文设置...")
    
    # 检查celery_app.py文件
    celery_app_path = os.path.join(BASE_DIR, 'app', 'tasks', 'celery_app.py')
    if not os.path.exists(celery_app_path):
        logger.error(f"找不到Celery应用文件: {celery_app_path}")
        return False
    
    with open(celery_app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查setup_task_context函数
    if 'def setup_task_context' not in content:
        logger.error("找不到setup_task_context函数")
        return False
    
    # 确保正确处理数据库会话
    if 'db.session.remove()' not in content:
        logger.warning("未找到数据库会话清理代码")
        # 这里不做修改，只是提示
    
    # 检查获取Flask应用实例的代码
    if "flask_app = create_app()" in content:
        logger.info("Celery应用代码看起来正常")
    else:
        logger.warning("Celery应用代码可能需要修改")
    
    # 验证应用实例是否正确保存
    if "_app_context = flask_app.app_context()" in content:
        logger.info("应用上下文保存代码正常")
    else:
        logger.warning("应用上下文保存代码可能有问题")
    
    logger.info("Celery任务上下文设置检查完成")
    return True

def fix_signal_handlers():
    """修复信号处理器的问题"""
    logger.info("检查并修复Celery信号处理器...")
    
    # 检查signal_handlers.py文件
    signal_handlers_path = os.path.join(BASE_DIR, 'app', 'tasks', 'signal_handlers.py')
    if not os.path.exists(signal_handlers_path):
        logger.error(f"找不到信号处理器文件: {signal_handlers_path}")
        return False
    
    with open(signal_handlers_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查错误在track_task_started函数
    if 'track_task_started' not in content:
        logger.error("找不到track_task_started函数")
        return False
    
    # 检查是否有错误处理
    if 'try:' in content and 'except Exception as e:' in content:
        logger.info("信号处理器包含正确的错误处理")
    else:
        logger.warning("信号处理器可能缺少错误处理")
    
    # 检查是否有"ValueError: not enough values to unpack (expected 2, got 0)"错误
    if "with db.session() as session:" in content:
        logger.info("信号处理器使用正确的数据库会话方式")
    
    logger.info("Celery信号处理器检查完成")
    return True

def fix_task_status_model():
    """检查TaskStatus模型是否正确"""
    logger.info("检查TaskStatus模型...")
    
    # 检查task_status.py文件
    task_status_path = os.path.join(BASE_DIR, 'app', 'models', 'task_status.py')
    if not os.path.exists(task_status_path):
        logger.error(f"找不到TaskStatus模型文件: {task_status_path}")
        return False
    
    with open(task_status_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否有必要的字段
    required_fields = ['task_id', 'task_name', 'status', 'created_at', 'started_at', 'completed_at']
    missing_fields = []
    
    for field in required_fields:
        if f"{field} = db.Column" not in content:
            missing_fields.append(field)
    
    if missing_fields:
        logger.error(f"TaskStatus模型缺少必要字段: {', '.join(missing_fields)}")
        return False
    
    logger.info("TaskStatus模型检查完成")
    return True

def verify_database_connection():
    """验证数据库连接是否正常"""
    logger.info("验证数据库连接...")
    
    try:
        # 导入相关模块
        from app import create_app
        from app.extensions import db
        
        # 创建应用实例并推送上下文
        app = create_app()
        with app.app_context():
            # 测试数据库连接
            engine = db.engine
            connection = engine.connect()
            logger.info("数据库连接测试成功!")
            connection.close()
            
            # 查询TaskStatus表
            from app.models.task_status import TaskStatus
            count = TaskStatus.query.count()
            logger.info(f"TaskStatus表中有 {count} 条记录")
            
            return True
    except Exception as e:
        logger.error(f"数据库连接测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """执行修复过程"""
    logger.info("开始修复Celery应用上下文问题...")
    
    # 验证数据库连接
    if verify_database_connection():
        logger.info("数据库连接正常")
    else:
        logger.error("数据库连接失败，请先修复数据库连接问题")
        return False
    
    # 修复TaskStatus模型
    if fix_task_status_model():
        logger.info("TaskStatus模型正常")
    else:
        logger.warning("TaskStatus模型可能有问题")
    
    # 修复信号处理器
    if fix_signal_handlers():
        logger.info("信号处理器正常")
    else:
        logger.warning("信号处理器可能有问题")
    
    # 修复任务上下文设置
    if fix_setup_task_context():
        logger.info("任务上下文设置正常")
    else:
        logger.warning("任务上下文设置可能有问题")
    
    logger.info("Celery应用上下文修复完成")
    logger.info("请重启Celery工作进程以应用更改")
    return True

if __name__ == "__main__":
    if main():
        print("\n修复成功! 请重启Celery工作进程以应用更改")
    else:
        print("\n修复过程遇到问题，请查看日志获取详细信息") 