#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

def get_membership_config():
    """获取会员配置信息"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        conn = sqlite3.connect('instance/essay_correction.db')
        cursor = conn.cursor()
        
        # 查询网站配置表中的会员配置
        cursor.execute("""
            SELECT config_name, config_value 
            FROM website_config 
            WHERE config_name IN (
                'free_essays', 'free_daily_limit',
                'regular_monthly_essays', 'regular_daily_essays',
                'premium_monthly_essays', 'premium_daily_essays'
            )
        """)
        
        config_data = cursor.fetchall()
        conn.close()
        
        # 构建配置字典
        config = {}
        for item in config_data:
            config[item[0]] = item[1]
        
        return config
    except Exception as e:
        print(f"查询会员配置出错: {e}")
        return None

# 创建测试用户函数
def create_test_users():
    """创建测试用户（普通会员和高级会员）"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        conn = sqlite3.connect('instance/essay_correction.db')
        cursor = conn.cursor()
        
        # 检查是否已存在测试用户
        cursor.execute("SELECT user_id FROM users WHERE username IN ('test_regular', 'test_premium')")
        existing_users = cursor.fetchall()
        
        if existing_users:
            print("测试用户已存在，跳过创建")
            conn.close()
            return
            
        # 创建普通会员测试账户
        cursor.execute("""
            INSERT INTO users (
                username, email, password_hash, created_at, 
                user_type, essays_remaining, essays_monthly_limit, essays_daily_limit, 
                essays_daily_used, essays_total_used, daily_reset_date, membership_expiry,
                registration_bonus_claimed, vip_status, is_active, role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test_regular', 'test_regular@example.com', 'pbkdf2:sha256:test', '2025-04-01 00:00:00',
            'regular', 300, 300, 30,
            0, 0, '2025-04-01', '2025-05-01',
            0, 0, 1, 'user'
        ))
        
        # 创建高级会员测试账户
        cursor.execute("""
            INSERT INTO users (
                username, email, password_hash, created_at, 
                user_type, essays_remaining, essays_monthly_limit, essays_daily_limit, 
                essays_daily_used, essays_total_used, daily_reset_date, membership_expiry,
                registration_bonus_claimed, vip_status, is_active, role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test_premium', 'test_premium@example.com', 'pbkdf2:sha256:test', '2025-04-01 00:00:00',
            'premium', 500, 500, 60,
            0, 0, '2025-04-01', '2025-05-01',
            0, 0, 1, 'user'
        ))
        
        conn.commit()
        conn.close()
        print("已创建测试用户：普通会员和高级会员")
    except Exception as e:
        print(f"创建测试用户出错: {e}")

if __name__ == "__main__":
    # 获取会员配置
    config = get_membership_config()
    
    if config:
        print("==== 会员等级配置 ====")
        print("\n免费用户配置:")
        print(f"总批改次数: {config.get('free_essays', '未设置')}")
        print(f"每日限制: {config.get('free_daily_limit', '未设置')}")
        
        print("\n普通会员配置:")
        print(f"每月批改次数: {config.get('regular_monthly_essays', '未设置')}")
        print(f"每日限制: {config.get('regular_daily_essays', '未设置')}")
        
        print("\n高级会员配置:")
        print(f"每月批改次数: {config.get('premium_monthly_essays', '未设置')}")
        print(f"每日限制: {config.get('premium_daily_essays', '未设置')}")
    else:
        print("未找到会员配置信息")
    
    # 自动创建参数
    auto_create = True
    
    # 查询现有会员测试账户
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        conn = sqlite3.connect('instance/essay_correction.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username, user_type, essays_remaining, essays_monthly_limit, 
                essays_daily_limit, membership_expiry
            FROM users 
            WHERE user_type IN ('regular', 'premium')
            LIMIT 10
        """)
        
        test_users = cursor.fetchall()
        conn.close()
        
        if test_users:
            print("\n==== 已有会员用户 ====")
            for user in test_users:
                print(f"用户: {user[0]}")
                print(f"  类型: {user[1]}")
                print(f"  剩余次数: {user[2]}")
                print(f"  月度限制: {user[3]}")
                print(f"  每日限制: {user[4]}")
                print(f"  到期日: {user[5]}")
                print("")
        else:
            print("\n没有找到会员用户")
            if auto_create:
                print("正在自动创建测试会员用户...")
                create_test_users()
            else:
                response = input("是否创建测试会员用户? (y/n): ")
                if response.lower() == 'y':
                    create_test_users()
    except Exception as e:
        print(f"查询会员用户出错: {e}") 