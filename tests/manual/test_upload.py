#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试文件上传和批改功能
"""

import requests
import os
import json

# 服务器URL
SERVER_URL = "http://localhost:5000"

def get_api_token():
    """获取API令牌"""
    login_data = {
        "username": "admin",  # 使用正确的用户名
        "password": "admin123",  # 使用正确的密码
        "login_type": "password"
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/api/v1/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')
            if token:
                print(f"成功获取API令牌")
                return token
        
        # 如果上面的方法失败，尝试通过标准登录
        print("API登录失败，尝试标准登录...")
        response = requests.post(f"{SERVER_URL}/login", data=login_data)
        
        if response.status_code == 200 or response.status_code == 302:
            print("标准登录成功!")
            # 检查响应中是否包含令牌
            try:
                result = response.json()
                token = result.get('access_token')
                if token:
                    print("从响应中获取到令牌")
                    return token
            except:
                pass
            
            # 获取cookies并尝试使用会话
            session = requests.Session()
            session.cookies.update(response.cookies)
            print("已保存会话cookies")
            
            # 尝试从用户信息端点获取令牌
            try:
                user_response = session.get(f"{SERVER_URL}/api/v1/auth/me")
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    if 'token' in user_data:
                        print("从用户信息中获取到令牌")
                        return user_data['token']
            except:
                pass
            
            # 如果还是无法获取令牌，返回会话对象代替
            return session
            
        print(f"登录失败! 状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return None
    except Exception as e:
        print(f"登录过程中出错: {str(e)}")
        return None

def test_upload_file():
    """测试文件上传和批改功能"""
    # 获取认证令牌或会话
    auth = get_api_token()
    if not auth:
        print("无法获取认证令牌或会话，测试失败")
        return False
    
    test_file_path = "test_essay.txt"
    
    # 确保测试文件存在
    if not os.path.exists(test_file_path):
        print(f"错误: 测试文件不存在 - {test_file_path}")
        return False
    
    # 准备上传文件
    with open(test_file_path, "rb") as f:
        files = {"file": (os.path.basename(test_file_path), f, "text/plain")}
        data = {"title": "测试作文上传"}  # 添加标题字段
        
        # 设置请求头和参数
        headers = {}
        if isinstance(auth, str):
            # 如果获取到了令牌，添加到请求头
            headers["Authorization"] = f"Bearer {auth}"
        
        # 发送请求
        try:
            if isinstance(auth, str):
                # 使用令牌发送请求
                response = requests.post(
                    f"{SERVER_URL}/api/v1/essays/file",
                    headers=headers,
                    files=files,
                    data=data
                )
            else:
                # 使用会话对象发送请求
                response = auth.post(
                    f"{SERVER_URL}/api/v1/essays/file",
                    files=files,
                    data=data
                )
            
            # 检查响应
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                print("上传成功!")
                print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"上传失败! 状态码: {response.status_code}")
                print(f"响应: {response.text}")
                return False
                
        except requests.exceptions.JSONDecodeError as e:
            print(f"解析JSON响应失败: {str(e)}")
            print(f"原始响应: {response.text}")
            return False
        except Exception as e:
            print(f"请求过程中出错: {str(e)}")
            return False

if __name__ == "__main__":
    test_upload_file() 