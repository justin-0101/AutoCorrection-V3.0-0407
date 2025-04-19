#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文提交API测试脚本
用于测试作文提交API是否可以正常工作
"""

import requests
import json
import sys

def test_submit_essay(url="http://localhost:5000/api/correction/submit"):
    """
    测试作文提交API
    
    Args:
        url: API地址，默认为http://localhost:5000/api/correction/submit
    """
    # 测试数据
    test_data = {
        "title": "测试作文",
        "content": "这是一篇测试作文。这是一篇测试作文的内容。请批改。" * 5,
        "grade": "高一",
        "async": True
    }
    
    print(f"正在测试API: {url}")
    print(f"发送数据: {json.dumps(test_data, ensure_ascii=False)}")
    
    try:
        # 发送请求
        response = requests.post(
            url,
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        # 打印响应
        print(f"\n状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            # 尝试解析为JSON
            result = response.json()
            print(f"响应内容(JSON): {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查返回的essay_id和task_id
            if "data" in result and "essay_id" in result["data"]:
                print(f"\n成功! 作文ID: {result['data']['essay_id']}")
                if "task_id" in result["data"]:
                    print(f"任务ID: {result['data']['task_id']}")
            else:
                print("\n警告: 响应中没有包含作文ID")
                
        except ValueError:
            # 非JSON响应
            print(f"响应内容(非JSON): {response.text[:500]}")
    
    except requests.exceptions.RequestException as e:
        print(f"\n请求出错: {e}")
    
if __name__ == "__main__":
    # 允许通过命令行参数指定URL
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000/api/correction/submit"
    test_submit_essay(url) 