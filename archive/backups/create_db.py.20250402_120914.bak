#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
初始化作文批改系统数据库
创建必要的表结构
"""

import sqlite3
import os
import datetime

# 数据库文件路径
DB_FILE = 'instance/essay_correction.db'

def init_db():
    """初始化数据库结构"""
    # 确保instance目录存在
    if not os.path.exists('instance'):
        os.makedirs('instance')
        
    # 检查数据库文件是否已存在
    db_exists = os.path.exists(DB_FILE)
    
    # 连接数据库（如果不存在则创建）
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 创建用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        role TEXT DEFAULT 'user',
        is_active BOOLEAN DEFAULT 1,
        user_type TEXT DEFAULT 'free'
    )''')
    
    # 创建用户资料表
    c.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
        profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        full_name TEXT,
        school TEXT,
        grade TEXT,
        avatar_path TEXT,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')
    
    # 创建验证码表
    c.execute('''CREATE TABLE IF NOT EXISTS verification_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        purpose TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        is_used BOOLEAN DEFAULT 0
    )''')
    
    # 创建登录历史表
    c.execute('''CREATE TABLE IF NOT EXISTS login_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')
    
    # 创建作文表
    c.execute('''CREATE TABLE IF NOT EXISTS essays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        content TEXT,
        submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        word_count INTEGER,
        total_score INTEGER,
        grade TEXT,
        content_score INTEGER,
        language_score INTEGER,
        structure_score INTEGER,
        writing_score INTEGER,
        spelling_errors TEXT,  /* JSON格式的错别字数据 */
        overall_assessment TEXT,
        content_analysis TEXT,
        language_analysis TEXT,
        structure_analysis TEXT,
        writing_analysis TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')
    
    # 创建会员计划表
    c.execute('''CREATE TABLE IF NOT EXISTS membership_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        duration_days INTEGER NOT NULL,
        features TEXT,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 创建会员订单表
    c.execute('''CREATE TABLE IF NOT EXISTS membership_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        plan_name TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        payment_time TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (plan_id) REFERENCES membership_plans(id)
    )''')
    
    # 添加会员过期时间字段到用户表（如果不存在）
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if 'membership_expiry' not in columns:
        c.execute('ALTER TABLE users ADD COLUMN membership_expiry TIMESTAMP')
    
    # 提交变更并关闭连接
    conn.commit()
    conn.close()
    
    print(f"数据库初始化完成: {DB_FILE}")
    return True

def init_membership_plans():
    """初始化会员套餐数据"""
    # 连接数据库
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 检查是否已有套餐数据
    c.execute("SELECT COUNT(*) FROM membership_plans")
    if c.fetchone()[0] == 0:
        # 插入默认套餐数据
        default_plans = [
            ('月度会员', '每月订阅，享受基础会员权益', 89.9, 30, '每月300篇作文批改额度，每日30篇限制', 1),
            ('季度会员', '3个月订阅，享受更多优惠', 239.9, 90, '每月300篇作文批改额度，每日30篇限制', 1),
            ('高级会员', '高级功能与更多批改额度', 129.9, 30, '每月500篇作文批改额度，每日60篇限制', 1)
        ]
        
        c.executemany('''
            INSERT INTO membership_plans 
            (name, description, price, duration_days, features, active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', default_plans)
        
        conn.commit()
        print("默认会员套餐数据初始化完成")
    
    conn.close()

if __name__ == "__main__":
    init_db()
    init_membership_plans() 