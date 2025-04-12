#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查status API是否正常工作
"""

import requests
import json
import time

def test_status_api():
    """测试status API是否正常工作"""
    # 测试不存在的essay_id
    essay_id = 8
    url = f"http://localhost:5000/api/v1/correction/essays/status/{essay_id}"
    
    print(f"测试URL: {url}")
    
    # 发送请求
    try:
        response = requests.get(url)
        
        # 打印状态码和响应内容
        print(f"状态码: {response.status_code}")
        try:
            data = response.json()
            print(f"响应内容: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"请求失败: {str(e)}")
    
    # 测试有效的essay_id
    valid_essay_id = 4  # 根据之前的检查，ID为4的作文是存在的
    valid_url = f"http://localhost:5000/api/v1/correction/essays/status/{valid_essay_id}"
    
    print(f"\n测试有效URL: {valid_url}")
    
    # 发送请求
    try:
        response = requests.get(valid_url)
        
        # 打印状态码和响应内容
        print(f"状态码: {response.status_code}")
        try:
            data = response.json()
            print(f"响应内容: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    test_status_api() 