#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单API授权测试
"""

import requests
import json

# 服务器URL
SERVER_URL = "http://localhost:5000"

def login():
    """登录并获取会话"""
    login_data = {
        "username": "admin",  # 使用正确的用户名
        "password": "admin123",  # 使用正确的密码
        "login_type": "password"
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/login", data=login_data)
        
        if response.status_code == 200 or response.status_code == 302:
            print("登录成功!")
            
            # 尝试从响应中获取令牌
            try:
                result = response.json()
                token = result.get('access_token')
                if token:
                    print(f"获取到令牌: {token}")
                    return token
            except:
                pass
            
            # 如果没有令牌，查看cookie
            if 'session' in response.cookies:
                print("获取到会话cookie")
                return response.cookies['session']
                
            print("获取令牌失败，检查响应内容")
            print(f"响应: {response.text}")
            return None
        else:
            print(f"登录失败! 状态码: {response.status_code}")
            print(f"响应: {response.text}")
            return None
    except Exception as e:
        print(f"登录过程中出错: {str(e)}")
        return None

def test_api():
    """测试API认证"""
    # 获取令牌或会话
    token = login()
    if not token:
        print("由于无法登录，无法继续测试")
        return False
    
    # 尝试访问API
    try:
        # 设置认证头
        headers = {"Authorization": f"Bearer {token}"}
        
        # 发送API请求
        response = requests.get(f"{SERVER_URL}/api/v1/essays", headers=headers)
        
        # 检查响应
        print(f"API请求状态码: {response.status_code}")
        try:
            print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        except:
            print(f"原始响应: {response.text}")
            
        return response.status_code == 200
    except Exception as e:
        print(f"API请求错误: {str(e)}")
        return False

if __name__ == "__main__":
    test_api() 