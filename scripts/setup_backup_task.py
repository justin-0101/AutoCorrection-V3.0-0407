#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置系统定期备份任务
支持在不同操作系统上配置自动备份任务
"""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup_backup')

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
PARENT_DIR = ROOT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 备份目录（与backup_system.py保持一致）
DEFAULT_BACKUP_DIR = os.environ.get('BACKUP_DIR', os.path.join(PARENT_DIR, 'AutoCorrection_Backups'))

def setup_cron_job(backup_cmd, schedule='0 2 * * *'):
    """
    在Linux/macOS上设置cron任务
    
    Args:
        backup_cmd: 完整的备份命令
        schedule: cron表达式，默认每天凌晨2点执行
    
    Returns:
        bool: 是否成功
    """
    try:
        # 获取当前用户的crontab内容
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout
        
        # 跳过已存在的任务
        if backup_cmd in current_crontab:
            logger.info("备份任务已经存在于crontab中")
            return True
        
        # 添加新的cron任务
        new_job = f"{schedule} {backup_cmd} > {ROOT_DIR}/logs/backup_cron.log 2>&1\n"
        new_crontab = current_crontab + new_job
        
        # 使用临时文件更新crontab
        temp_file = os.path.join(ROOT_DIR, 'temp_crontab')
        with open(temp_file, 'w') as f:
            f.write(new_crontab)
        
        # 安装新的crontab
        result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
        
        # 删除临时文件
        os.remove(temp_file)
        
        if result.returncode == 0:
            logger.info(f"成功设置cron任务: {new_job.strip()}")
            return True
        else:
            logger.error(f"设置cron任务失败: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"设置cron任务时出错: {str(e)}")
        return False


def setup_windows_task(backup_script, schedule='02:00', interval=None):
    """
    在Windows上设置计划任务
    
    Args:
        backup_script: 备份脚本的完整路径
        schedule: 任务执行时间，默认为02:00（凌晨2点）
        interval: 间隔时间（分钟），如果设置则使用间隔触发器而非每日触发器
    
    Returns:
        bool: 是否成功
    """
    try:
        # 构建任务名称
        task_name = "AutoCorrectionSystemBackup"
        
        # 检查任务是否已存在
        check_cmd = ['schtasks', '/query', '/tn', task_name]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"备份任务已存在: {task_name}")
            
            # 删除现有任务以便更新
            delete_cmd = ['schtasks', '/delete', '/tn', task_name, '/f']
            subprocess.run(delete_cmd, capture_output=True)
        
        # 激活Python虚拟环境（如果存在）
        python_exe = sys.executable
        venv_dir = os.path.join(ROOT_DIR, 'venv')
        if os.path.exists(venv_dir):
            python_exe = os.path.join(venv_dir, 'Scripts', 'python.exe')
        
        # 准备命令
        command = f'"{python_exe}" "{backup_script}"'
        
        # 创建新任务
        if interval:
            # 使用MINUTE间隔触发器
            create_cmd = [
                'schtasks', '/create', '/tn', task_name,
                '/tr', command,
                '/sc', 'MINUTE',
                '/mo', str(interval),  # 间隔分钟数
                '/ru', 'SYSTEM',  # 使用SYSTEM账户运行，确保有权限
                '/f'  # 强制创建，覆盖现有任务
            ]
            trigger_desc = f"每{interval}分钟"
        else:
            # 使用DAILY触发器
            create_cmd = [
                'schtasks', '/create', '/tn', task_name,
                '/tr', command,
                '/sc', 'daily',
                '/st', schedule,
                '/ru', 'SYSTEM',  # 使用SYSTEM账户运行，确保有权限
                '/f'  # 强制创建，覆盖现有任务
            ]
            trigger_desc = f"每天 {schedule}"
        
        result = subprocess.run(create_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"成功设置Windows计划任务: {task_name}，执行时间: {trigger_desc}")
            return True
        else:
            logger.error(f"设置Windows计划任务失败: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"设置Windows计划任务时出错: {str(e)}")
        return False


def create_backup_bat(backup_script, backup_dir):
    """
    创建Windows批处理文件
    
    Args:
        backup_script: 备份脚本的完整路径
        backup_dir: 备份目录路径
    
    Returns:
        str: 批处理文件路径
    """
    bat_path = os.path.join(ROOT_DIR, 'scripts', 'run_backup.bat')
    
    # 激活Python虚拟环境（如果存在）
    venv_dir = os.path.join(ROOT_DIR, 'venv')
    if os.path.exists(venv_dir):
        activate_cmd = f'call "{os.path.join(venv_dir, "Scripts", "activate.bat")}"\n'
    else:
        activate_cmd = ''
    
    # 批处理文件内容
    bat_content = f"""@echo off
cd /d "{ROOT_DIR}"
{activate_cmd}python "{backup_script}" --backup-dir "{backup_dir}" > "{os.path.join(ROOT_DIR, 'logs', 'backup.log')}" 2>&1
"""
    
    # 写入批处理文件
    with open(bat_path, 'w') as f:
        f.write(bat_content)
    
    logger.info(f"已创建备份批处理文件: {bat_path}")
    return bat_path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='设置作文批改系统定期备份任务')
    parser.add_argument('--schedule', type=str, default=None,
                        help='备份时间，Linux/macOS使用cron表达式，Windows使用HH:MM格式')
    parser.add_argument('--interval', type=int, default=None,
                        help='备份间隔（分钟），如果设置则优先于schedule参数')
    parser.add_argument('--backup-dir', type=str, default=DEFAULT_BACKUP_DIR,
                        help=f'备份目录路径，默认为{DEFAULT_BACKUP_DIR}')
    parser.add_argument('--show-only', action='store_true',
                        help='仅显示命令，不实际设置')
    
    args = parser.parse_args()
    
    # 确定操作系统
    system = platform.system()
    
    # 确定备份脚本路径
    backup_script = os.path.join(ROOT_DIR, 'scripts', 'backup_system.py')
    
    if not os.path.exists(backup_script):
        logger.error(f"备份脚本不存在: {backup_script}")
        return 1
    
    # 将备份目录作为参数传递给备份脚本
    backup_cmd = f'"{backup_script}" --backup-dir "{args.backup_dir}"'
    
    if system == 'Linux' or system == 'Darwin':  # Linux或macOS
        if args.interval:
            # 对于cron，使用*/interval格式表示每interval分钟运行一次
            schedule = f"*/{args.interval} * * * *"
            logger.info(f"配置为每{args.interval}分钟运行一次备份")
        else:
            schedule = args.schedule or '0 2 * * *'  # 默认每天凌晨2点
        
        if args.show_only:
            print(f"将添加以下cron任务:")
            print(f"{schedule} {backup_cmd} > {ROOT_DIR}/logs/backup_cron.log 2>&1")
        else:
            setup_cron_job(backup_cmd, schedule)
    
    elif system == 'Windows':
        # 创建批处理文件（Windows任务计划程序更适合运行.bat）
        bat_path = create_backup_bat(backup_script, args.backup_dir)
        
        if args.interval:
            if args.show_only:
                print(f"将添加以下Windows计划任务:")
                print(f"任务名称: AutoCorrectionSystemBackup")
                print(f"执行命令: {bat_path}")
                print(f"执行频率: 每{args.interval}分钟")
            else:
                setup_windows_task(bat_path, interval=args.interval)
        else:
            schedule = args.schedule or '02:00'  # 默认凌晨2点
            if args.show_only:
                print(f"将添加以下Windows计划任务:")
                print(f"任务名称: AutoCorrectionSystemBackup")
                print(f"执行命令: {bat_path}")
                print(f"执行时间: 每天 {schedule}")
            else:
                setup_windows_task(bat_path, schedule=schedule)
    
    else:
        logger.error(f"不支持的操作系统: {system}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main()) 