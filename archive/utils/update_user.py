#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime

def update_user_to_free(username):
    """将用户更新为免费用户"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        conn = sqlite3.connect('instance/essay_correction.db')
        cursor = conn.cursor()
        
        # 获取当前用户信息
        cursor.execute("SELECT user_id, essays_total_used FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        
        if not user_data:
            print(f"未找到用户 {username}")
            conn.close()
            return False
        
        user_id, essays_total_used = user_data
        
        # 免费用户配置
        free_essays = 13  # 初始10篇 + 3篇注册奖励
        daily_limit = 5
        
        # 计算剩余次数
        remaining = max(0, free_essays - essays_total_used)
        
        # 更新用户为免费用户
        cursor.execute("""
            UPDATE users SET 
                user_type = 'free',
                essays_remaining = ?,
                essays_monthly_limit = ?,
                essays_daily_limit = ?,
                membership_expiry = NULL
            WHERE user_id = ?
        """, (remaining, free_essays, daily_limit, user_id))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"更新用户信息出错: {e}")
        return False

if __name__ == "__main__":
    # 更新 juschen 用户为免费用户
    if update_user_to_free("juschen"):
        print("已成功将用户 juschen 更新为免费用户")
    else:
        print("更新用户失败") 