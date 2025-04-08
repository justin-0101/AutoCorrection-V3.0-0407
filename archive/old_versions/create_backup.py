#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
备份数据库和主要配置文件
"""

import os
import shutil
from datetime import datetime

def create_backup():
    """创建数据库和主要配置文件的备份"""
    # 备份目录
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 生成时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 备份数据库
    db_file = 'instance/essay_correction.db'
    if os.path.exists(db_file):
        db_backup = f'{backup_dir}/essay_correction_{timestamp}.db'
        shutil.copy2(db_file, db_backup)
        print(f'数据库已备份到: {db_backup}')
    else:
        print(f'警告: 数据库文件 {db_file} 不存在')
    
    # 备份主要配置文件
    config_files = ['app.py', 'config.py', 'create_db.py']
    for file in config_files:
        if os.path.exists(file):
            backup_file = f'{backup_dir}/{file}_{timestamp}.backup'
            shutil.copy2(file, backup_file)
            print(f'{file} 已备份到: {backup_file}')
        else:
            print(f'警告: 配置文件 {file} 不存在')
    
    # 创建备份记录
    backup_log = f'{backup_dir}/backup_log_{timestamp}.txt'
    with open(backup_log, 'w', encoding='utf-8') as f:
        f.write(f'备份时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'备份数据库: {db_file}\n')
        f.write(f'备份配置文件: {", ".join(config_files)}\n')
    
    print(f'备份完成! 备份日志: {backup_log}')

if __name__ == "__main__":
    create_backup() 