#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文文件上传测试脚本
用于测试作文文件上传API
"""

import requests
import sys
import os
from pathlib import Path

def create_test_file():
    """创建测试文件"""
    test_file_path = "test_essay_upload.txt"
    
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("这是一篇测试作文。\n")
        f.write("这是第二段内容。这里有一些批改内容。\n")
        f.write("这是第三段，测试文件上传功能。\n")
    
    print(f"已创建测试文件: {test_file_path}")
    return test_file_path

def test_file_upload(url="http://localhost:5000/api/correction/submit"):
    """
    测试作文文件上传
    
    Args:
        url: API地址
    """
    # 创建测试文件
    test_file_path = create_test_file()
    
    # 表单数据
    form_data = {
        "title": "测试文件上传",
        "grade": "高一"
    }
    
    # 文件数据
    files = {
        "file": open(test_file_path, "rb")
    }
    
    print(f"正在测试文件上传API: {url}")
    print(f"表单数据: {form_data}")
    print(f"文件: {test_file_path}")
    
    try:
        # 发送请求
        response = requests.post(
            url,
            data=form_data,
            files=files
        )
        
        # 打印响应
        print(f"\n状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            # 尝试解析为JSON
            result = response.json()
            print(f"响应内容(JSON):\n{result}")
        except:
            # 非JSON响应
            print(f"响应内容(非JSON):\n{response.text[:500]}")
        
    except requests.exceptions.RequestException as e:
        print(f"\n请求出错: {e}")
    
    finally:
        # 关闭文件
        files["file"].close()

def test_multiple_endpoints():
    """测试多个可能的API终端"""
    endpoints = [
        "/api/correction/submit",
        "/api/essays/submit",
        "/api/essays/upload",
        "/api/correction/upload"
    ]
    
    base_url = "http://localhost:5000"
    
    for endpoint in endpoints:
        print(f"\n\n===== 测试终端: {endpoint} =====")
        test_file_upload(f"{base_url}{endpoint}")

if __name__ == "__main__":
    # 如果提供了命令行参数，使用它作为URL
    if len(sys.argv) > 1:
        test_file_upload(sys.argv[1])
    else:
        # 否则测试多个可能的终端
        test_multiple_endpoints() 