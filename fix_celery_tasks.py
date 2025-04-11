#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复Celery任务问题脚本
这个脚本用于修复Celery任务中的logger未定义和应用上下文问题
"""

import os
import sys
import logging
import re
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('celery_fix')

# 确保工作目录正确
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

def fix_logger_import():
    """修复correction_tasks.py中的logger引用问题"""
    file_path = os.path.join(project_root, 'app', 'tasks', 'correction_tasks.py')
    logger.info(f"正在修复文件: {file_path}")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 查找logger导入语句
    import_pattern = r'from app\.tasks\.logging_config import get_task_logger'
    logger_pattern = r'logger = get_task_logger\(\)'
    
    has_import = bool(re.search(import_pattern, content))
    has_logger_init = bool(re.search(logger_pattern, content))
    
    if has_import and has_logger_init:
        logger.info("文件已包含正确的logger导入和初始化语句")
    else:
        # 如果缺少导入语句，添加它
        if not has_import:
            # 在最后一个import语句后添加
            import_section_end = 0
            for match in re.finditer(r'^import|^from', content, re.MULTILINE):
                line_end = content.find('\n', match.start())
                if line_end > import_section_end:
                    import_section_end = line_end
            
            if import_section_end > 0:
                new_content = (content[:import_section_end+1] + 
                              "from app.tasks.logging_config import get_task_logger\n" + 
                              content[import_section_end+1:])
                content = new_content
                logger.info("添加了logger导入语句")
        
        # 如果缺少logger初始化，添加它
        if not has_logger_init:
            # 在所有导入语句之后添加logger初始化
            import_section_end = 0
            for match in re.finditer(r'^import|^from', content, re.MULTILINE):
                line_end = content.find('\n', match.start())
                if line_end > import_section_end:
                    import_section_end = line_end
            
            if import_section_end > 0:
                # 寻找导入部分之后的一个空行
                next_empty_line = content.find('\n\n', import_section_end)
                if next_empty_line > 0:
                    new_content = (content[:next_empty_line+2] + 
                                  "# 获取任务专用日志记录器\nlogger = get_task_logger()\n\n" + 
                                  content[next_empty_line+2:])
                    content = new_content
                    logger.info("添加了logger初始化语句")
        
        # 保存修改后的内容
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        logger.info("修复了correction_tasks.py中的logger问题")

def fix_app_context_issue():
    """修复Celery任务中的应用上下文问题"""
    file_path = os.path.join(project_root, 'app', 'tasks', 'celery_app.py')
    logger.info(f"正在修复文件: {file_path}")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 检查setup_task_context函数中的应用上下文设置
    setup_task_context_pattern = r'@task_prerun\.connect[\s\n]*def setup_task_context\(.*?\):'
    context_check_pattern = r'if not flask_app:.*?logger\.error\("任务执行前应用实例未初始化"\)'
    
    setup_task_context_match = re.search(setup_task_context_pattern, content, re.DOTALL)
    
    if setup_task_context_match:
        # 查找函数体
        func_start = setup_task_context_match.end()
        # 找到函数体的结束（下一个装饰器或函数定义）
        next_func = re.search(r'@|def\s+[a-zA-Z_]+\s*\(', content[func_start:], re.DOTALL)
        if next_func:
            func_end = func_start + next_func.start()
            func_body = content[func_start:func_end]
            
            # 检查是否有应用上下文检查
            if re.search(context_check_pattern, func_body, re.DOTALL):
                # 确保正确地创建应用上下文
                if "task._app_context = flask_app.app_context()" in func_body:
                    # 确保清理数据库会话
                    if "db.session.remove()" in func_body:
                        logger.info("setup_task_context函数中已存在正确的应用上下文和数据库会话处理")
                    else:
                        # 添加数据库会话清理
                        new_func_body = func_body.replace(
                            "task._app_context = flask_app.app_context()",
                            "task._app_context = flask_app.app_context()\n        task._app_context.push()\n        \n        # 确保数据库会话\n        from app.extensions import db\n        db.session.remove()"
                        )
                        content = content.replace(func_body, new_func_body)
                        logger.info("在setup_task_context函数中添加了数据库会话清理")
                else:
                    # 添加正确的应用上下文处理
                    new_func_body = func_body.replace(
                        "logger.info(f\"为任务 {task_id} 创建应用上下文\")",
                        "logger.info(f\"为任务 {task_id} 创建应用上下文\")\n        task._app_context = flask_app.app_context()\n        task._app_context.push()\n        \n        # 确保数据库会话\n        from app.extensions import db\n        db.session.remove()"
                    )
                    content = content.replace(func_body, new_func_body)
                    logger.info("在setup_task_context函数中添加了应用上下文处理")
            else:
                logger.warning("setup_task_context函数中缺少应用上下文检查")
        else:
            logger.warning("无法确定setup_task_context函数的结束位置")
    else:
        logger.warning("找不到setup_task_context函数")
    
    # 保存修改后的内容
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    logger.info("修复了Celery任务中的应用上下文问题")

def fix_task_unpack_error():
    """修复Celery任务中的unpacking错误问题"""
    file_path = os.path.join(project_root, 'app', 'tasks', 'signal_handlers.py')
    logger.info(f"正在修复文件: {file_path}")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 查找可能导致unpacking错误的代码
    task_functions = {
        'track_task_started': '@task_prerun.connect\ndef track_task_started',
        'track_task_success': '@task_success.connect\ndef track_task_success',
        'track_task_failure': '@task_failure.connect\ndef track_task_failure',
        'track_task_retry': '@task_retry.connect\ndef track_task_retry'
    }
    
    for func_name, func_pattern in task_functions.items():
        func_match = re.search(func_pattern, content)
        if func_match:
            # 找到函数定义
            func_start = func_match.start()
            # 找到函数体的结束（下一个装饰器或函数定义）
            next_func = re.search(r'@|def\s+[a-zA-Z_]+\s*\(', content[func_start+len(func_pattern):], re.DOTALL)
            if next_func:
                func_end = func_start + len(func_pattern) + next_func.start()
                func_body = content[func_start:func_end]
                
                # 检查是否有可能导致unpacking错误的代码
                if "_loc" in func_body:
                    logger.warning(f"在函数 {func_name} 中找到可能导致unpacking错误的代码: _loc")
                    # 添加安全的解包处理
                    new_func_body = func_body.replace(
                        "tasks, accept, hostname = _loc",
                        "try:\n        tasks, accept, hostname = _loc\n    except ValueError:\n        logger.warning(f\"[信号处理] 无法解包_loc变量: {_loc}\")\n        tasks, accept, hostname = None, None, None"
                    )
                    content = content.replace(func_body, new_func_body)
                    logger.info(f"修复了函数 {func_name} 中的unpacking错误")
    
    # 保存修改后的内容
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    logger.info("修复了Celery任务中的unpacking错误问题")

def main():
    """主函数"""
    logger.info("开始修复Celery任务问题...")
    
    try:
        # 修复logger导入问题
        fix_logger_import()
        
        # 修复应用上下文问题
        fix_app_context_issue()
        
        # 修复unpacking错误问题
        fix_task_unpack_error()
        
        logger.info("修复完成")
    except Exception as e:
        logger.error(f"修复过程中发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    if main():
        print("Celery任务问题修复完成")
    else:
        print("Celery任务问题修复失败")
        sys.exit(1) 