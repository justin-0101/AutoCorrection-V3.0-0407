#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接API测试脚本
"""

import requests
import json

# 服务器URL
SERVER_URL = "http://localhost:5000"

# 设置直接的API密钥（模拟）
API_KEY = "test_api_key"

def test_api():
    """直接测试API，使用API密钥"""
    try:
        # 设置认证头
        headers = {"X-API-KEY": API_KEY}
        
        # 发送API请求
        response = requests.get(f"{SERVER_URL}/api/v1/essays/file-types", headers=headers)
        
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