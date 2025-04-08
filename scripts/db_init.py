#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
初始化作文批改系统数据库
创建必要的表结构和初始数据
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_init')

from database.db_manager import db_manager
from database.migrations import run_migrations
from werkzeug.security import generate_password_hash

def init_db():
    """初始化数据库结构和基础数据"""
    logger.info("开始初始化数据库...")
    
    # 确保实例目录存在
    instance_dir = os.path.join(root_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
    # 运行数据库迁移
    run_migrations()
    
    # 创建管理员账号(如果不存在)
    with db_manager.get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            # 创建管理员账号
            cursor.execute(
                """
                INSERT INTO users 
                (username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                ('admin', 'admin@example.com', generate_password_hash('admin123'), 'admin', 1)
            )
            
            # 获取新插入的admin_id
            cursor.execute("SELECT user_id FROM users WHERE username = 'admin'")
            admin_id = cursor.fetchone()[0]
            
            # 创建管理员资料
            cursor.execute(
                """
                INSERT INTO user_profiles
                (user_id, full_name, school, grade)
                VALUES (?, ?, ?, ?)
                """,
                (admin_id, '系统管理员', '管理平台', '管理员')
            )
            
            logger.info("管理员账号创建成功")
        else:
            logger.info("管理员账号已存在，跳过创建")
    
    logger.info("数据库初始化完成")

if __name__ == '__main__':
    init_db() 