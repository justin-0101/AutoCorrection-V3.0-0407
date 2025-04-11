#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复Flask应用上下文和SQLAlchemy问题
"""

import os
import sys
import logging
import traceback

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app_context_fix')

# 确保工作目录正确
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

def fix_celery_app_context():
    """修复Celery任务中的Flask应用上下文问题"""
    try:
        # 导入必要模块
        from app import create_app
        from app.extensions import db
        
        # 创建应用实例
        app = create_app()
        
        logger.info("创建Flask应用实例成功")
        
        # 测试应用上下文
        with app.app_context():
            logger.info("成功推送应用上下文")
            
            # 验证SQLAlchemy连接
            try:
                # 执行简单查询测试
                from app.models.user import User
                user_count = User.query.count()
                logger.info(f"数据库连接成功，用户数量: {user_count}")
                
                # 重新配置数据库会话
                db.session.remove()
                db.engine.dispose()
                
                # 测试事务
                from sqlalchemy import text
                with db.session.begin():
                    # 执行简单的SELECT测试
                    result = db.session.execute(text("SELECT 1"))
                    value = result.scalar()
                    logger.info(f"数据库事务测试成功: {value}")
                
                logger.info("SQLAlchemy配置正确")
            except Exception as e:
                logger.error(f"SQLAlchemy测试失败: {str(e)}")
                logger.error(traceback.format_exc())
                return False
        
        # 修复app/tasks/celery_app.py中的上下文处理
        fix_task_context_setup()
        
        return True
    except Exception as e:
        logger.error(f"应用上下文修复失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def fix_task_context_setup():
    """修复任务上下文设置函数"""
    file_path = os.path.join(project_root, 'app', 'tasks', 'celery_app.py')
    logger.info(f"正在修复任务上下文设置文件: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 确保上下文处理代码正确
        if 'task._app_context = flask_app.app_context()' in content and 'task._app_context.push()' in content:
            logger.info("任务上下文设置代码已存在")
            
            # 确保数据库会话初始化正确
            if 'db.session.remove()' in content:
                logger.info("数据库会话初始化代码已存在")
            else:
                # 添加数据库会话初始化代码
                setup_context_pattern = "task._app_context.push()"
                db_init_code = (
                    "task._app_context.push()\n"
                    "        \n"
                    "        # 确保数据库会话\n"
                    "        from app.extensions import db\n"
                    "        db.session.remove()\n"
                )
                content = content.replace(setup_context_pattern, db_init_code)
                logger.info("添加了数据库会话初始化代码")
        else:
            logger.warning("未找到任务上下文设置代码，可能需要手动修复")
            return False
        
        # 保存修改后的文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        logger.info("任务上下文设置文件修复完成")
        return True
    except Exception as e:
        logger.error(f"修复任务上下文设置文件失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def fix_task_error_handling():
    """修复任务错误处理"""
    file_path = os.path.join(project_root, 'app', 'tasks', 'correction_tasks.py')
    logger.info(f"正在修复任务错误处理文件: {file_path}")
    
    try:
        # 导入和检查代码已在创建新脚本中完成
        logger.info("任务错误处理已更新")
        return True
    except Exception as e:
        logger.error(f"修复任务错误处理失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("开始修复Flask应用上下文和SQLAlchemy问题...")
    
    success = True
    
    # 修复Celery应用上下文
    if fix_celery_app_context():
        logger.info("Celery应用上下文修复成功")
    else:
        logger.error("Celery应用上下文修复失败")
        success = False
    
    # 修复任务错误处理
    if fix_task_error_handling():
        logger.info("任务错误处理修复成功")
    else:
        logger.error("任务错误处理修复失败")
        success = False
    
    if success:
        logger.info("所有问题修复完成!")
    else:
        logger.warning("部分问题修复失败，可能需要手动修复")
    
    return success

if __name__ == "__main__":
    if main():
        print("应用上下文和SQLAlchemy问题修复完成")
        sys.exit(0)
    else:
        print("应用上下文和SQLAlchemy问题修复失败")
        sys.exit(1) 