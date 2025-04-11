#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery任务修复工具
专门修复 'ValueError: not enough values to unpack (expected 3, got 0)' 错误
"""

import os
import sys
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("celery_task_fix")

# 获取项目根目录
BASE_DIR = Path(__file__).parent.absolute()
logger.info(f"项目根目录: {BASE_DIR}")

def verify_celery_app():
    """验证Celery应用设置是否正确"""
    celery_app_path = os.path.join(BASE_DIR, 'app', 'tasks', 'celery_app.py')
    if not os.path.exists(celery_app_path):
        logger.error(f"找不到Celery应用文件: {celery_app_path}")
        return False
    
    try:
        from app.tasks.celery_app import celery_app
        logger.info(f"成功导入celery_app: {celery_app}")
        return True
    except Exception as e:
        logger.error(f"导入celery_app时出错: {str(e)}")
        return False

def fix_task_setup():
    """修复任务设置,特别是解决'not enough values to unpack'错误"""
    # 检查并修复 app/tasks/__init__.py 文件
    init_path = os.path.join(BASE_DIR, 'app', 'tasks', '__init__.py')
    if not os.path.exists(init_path):
        logger.warning(f"找不到 {init_path}, 创建新文件")
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n"""\nCelery任务包\n用于注册和管理异步任务\n"""\n\n# 导入celery实例以便其他模块可以访问\nfrom app.tasks.celery_app import celery_app\n\n# 导入所有任务模块以确保它们被注册\nfrom app.tasks import correction_tasks\n\n__all__ = ["celery_app"]\n')
        logger.info(f"已创建 {init_path}")
    else:
        # 验证__init__.py文件内容
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'from app.tasks.celery_app import celery_app' not in content:
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write('#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n"""\nCelery任务包\n用于注册和管理异步任务\n"""\n\n# 导入celery实例以便其他模块可以访问\nfrom app.tasks.celery_app import celery_app\n\n# 导入所有任务模块以确保它们被注册\nfrom app.tasks import correction_tasks\n\n__all__ = ["celery_app"]\n')
            logger.info(f"已更新 {init_path}")
        else:
            logger.info(f"{init_path} 内容正确，无需修改")
    
    return True

def update_start_celery_script():
    """更新Celery启动脚本"""
    celery_script_path = os.path.join(BASE_DIR, 'scripts', 'start_celery.py')
    if not os.path.exists(celery_script_path):
        logger.error(f"找不到Celery启动脚本: {celery_script_path}")
        return False
    
    # 读取现有脚本
    with open(celery_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否需要修改celery应用路径
    if "app.tasks:celery" in content:
        content = content.replace("app.tasks:celery", "app.tasks.celery_app:celery_app")
        with open(celery_script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"已更新 {celery_script_path} 中的Celery应用路径")
    elif "app.tasks.celery_app:celery_app" in content:
        logger.info(f"{celery_script_path} 中的Celery应用路径已正确，无需修改")
    
    return True

def main():
    """执行所有修复步骤"""
    logger.info("开始修复Celery任务问题...")
    
    # 验证celery应用
    if verify_celery_app():
        logger.info("Celery应用验证成功")
    else:
        logger.warning("Celery应用验证失败，可能需要手动修复")
    
    # 修复任务设置
    if fix_task_setup():
        logger.info("任务设置修复完成")
    else:
        logger.warning("任务设置修复失败，可能需要手动修复")
    
    # 更新启动脚本
    if update_start_celery_script():
        logger.info("启动脚本更新成功")
    else:
        logger.warning("启动脚本更新失败，可能需要手动修复")
    
    logger.info("所有修复步骤已完成")
    
    return True

if __name__ == "__main__":
    if main():
        print("\n修复完成! 请重启Celery工作进程以应用更改")
    else:
        print("\n修复过程遇到问题，请查看日志获取详细信息") 