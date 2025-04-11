#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import re
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("celery_logger_fix")

def fix_task_logger():
    """修复Celery任务中的logger问题"""
    
    # 修复correction_tasks.py中的logger问题
    correction_tasks_path = os.path.join('app', 'tasks', 'correction_tasks.py')
    if os.path.exists(correction_tasks_path):
        logger.info(f"开始修复 {correction_tasks_path} 中的logger问题")
        
        with open(correction_tasks_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已正确导入logger
        if not re.search(r'logger\s*=\s*logging\.getLogger\(__name__\)', content):
            logger.info("需要添加logger定义")
            
            # 查找导入logging语句
            if 'import logging' not in content:
                # 添加导入语句
                content = re.sub(
                    r'(import .*?\n)',
                    r'\1import logging\n',
                    content,
                    count=1
                )
                logger.info("已添加logging导入")
            
            # 添加logger定义
            content = re.sub(
                r'(from\s+app\.models\.task_status.*?\n)',
                r'\1\nlogger = logging.getLogger(__name__)\n',
                content,
                count=1
            )
            logger.info("已添加logger定义")
            
            # 保存更改
            with open(correction_tasks_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"{correction_tasks_path} 已更新")
        else:
            logger.info("logger已正确定义，无需修改")
    else:
        logger.warning(f"找不到文件: {correction_tasks_path}")
    
    # 修复celery_app.py中的应用上下文问题
    celery_app_path = os.path.join('app', 'tasks', 'celery_app.py')
    if os.path.exists(celery_app_path):
        logger.info(f"开始修复 {celery_app_path} 中的应用上下文问题")
        
        with open(celery_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查setup_task_context函数是否正确配置
        if 'setup_task_context' in content:
            # 确保Flask应用上下文正确推送和数据库会话正确初始化
            pattern = r'def setup_task_context.*?task\._app_context\.push\(\)(.*?)logger\.info'
            match = re.search(pattern, content, re.DOTALL)
            
            if match and 'db.session.remove()' in match.group(1):
                logger.info("Task上下文设置看起来正确，无需修改")
            else:
                logger.info("需要修复Task上下文设置")
                
                # 修复task_prerun函数，确保正确初始化数据库会话
                content = re.sub(
                    r'(task\._app_context\.push\(\)\s*\n)(\s+logger\.info)',
                    r'\1        \n        # 确保数据库会话\n        from app.extensions import db\n        db.session.remove()\n\n\2',
                    content
                )
                
                # 保存更改
                with open(celery_app_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"{celery_app_path} 中的Task上下文设置已修复")
        else:
            logger.warning("找不到setup_task_context函数")
    else:
        logger.warning(f"找不到文件: {celery_app_path}")
    
    logger.info("Celery任务logger问题修复完成")

if __name__ == "__main__":
    logger.info("开始修复Celery任务logger问题...")
    fix_task_logger()
    logger.info("修复完成，请重启Celery工作进程以应用更改") 