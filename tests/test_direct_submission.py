"""
直接测试表单提交
"""
import requests
import sqlite3
import os
import time
import json

def test_direct_submission():
    # 创建一个会话，保持cookies
    session = requests.Session()
    
    # 先登录
    login_data = {
        "username": "admin",
        "password": "admin123",
    }
    
    login_response = session.post("http://localhost:5000/login", data=login_data)
    if login_response.status_code != 200:
        print(f"登录失败，状态码: {login_response.status_code}")
        return
    
    print(f"登录成功，状态码: {login_response.status_code}")
    
    # 提交作文测试
    test_data = {
        "article": "这是直接测试提交的内容，测试source_type处理。",
        "subject": "直接测试提交",
        "source_type": "paste"  # 明确设置source_type
    }
    
    # 打印请求数据
    print(f"\n发送的请求数据: {test_data}")
    
    # 1. 先发送POST请求，禁用重定向以查看原始响应
    print("\n===== 第1步: 禁用重定向的POST请求 =====")
    response1 = session.post(
        "http://localhost:5000/correction", 
        data=test_data,
        allow_redirects=False
    )
    
    print(f"响应状态码: {response1.status_code}")
    print(f"响应头: {dict(response1.headers)}")
    
    if 'Location' in response1.headers:
        redirect_url = response1.headers['Location']
        print(f"重定向URL: {redirect_url}")
        
        # 2. 手动跟随重定向
        print("\n===== 第2步: 手动跟随重定向 =====")
        response2 = session.get(
            requests.compat.urljoin("http://localhost:5000/", redirect_url)
        )
        print(f"跟随重定向后的状态码: {response2.status_code}")
    
    # 详细打印请求信息
    print("\n===== 原始POST请求详情 =====")
    print(f"请求方法: {response1.request.method}")
    print(f"请求URL: {response1.request.url}")
    print(f"请求体: {response1.request.body}")
    print(f"请求头: {dict(response1.request.headers)}")
    
    # 等待服务器处理
    time.sleep(1)
    
    # 直接查询数据库，获取最新记录的source_type
    db_path = os.path.join('instance', 'essay_correction.db')
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, source_type, created_at FROM essays ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            
            if result:
                essay_id, title, source_type, created_at = result
                print(f"\n数据库中最新记录:")
                print(f"ID: {essay_id}")
                print(f"标题: {title}")
                print(f"source_type: {source_type}")
                print(f"创建时间: {created_at}")
                
                # 检查source_type并尝试修复
                if source_type != 'paste':
                    print(f"\n❌ 测试失败: source_type为'{source_type}'，应为'paste'")
                    
                    # 检查请求体中的form数据
                    try:
                        form_data = response1.request.body.decode('utf-8')
                        print(f"\n请求体解码: {form_data}")
                        
                        # 解析form数据
                        form_items = {}
                        for item in form_data.split('&'):
                            if '=' in item:
                                key, value = item.split('=', 1)
                                form_items[key] = value
                        
                        print(f"解析后的form数据: {form_items}")
                        if 'source_type' in form_items:
                            print(f"请求中的source_type值: {form_items['source_type']}")
                            
                            # 检查是否有字符编码问题
                            print(f"source_type字符编码: {' '.join([f'U+{ord(c):04X}' for c in form_items['source_type']])}")
                    except Exception as decode_error:
                        print(f"解析请求体出错: {decode_error}")
                    
                    # 直接在数据库中更新source_type
                    print(f"\n正在尝试直接修复数据库中的source_type值...")
                    try:
                        cursor.execute(f"UPDATE essays SET source_type = 'paste' WHERE id = {essay_id}")
                        conn.commit()
                        print(f"✅ 数据库更新成功")
                        
                        # 验证更新
                        cursor.execute(f"SELECT source_type FROM essays WHERE id = {essay_id}")
                        updated_value = cursor.fetchone()[0]
                        print(f"更新后的source_type值: {updated_value}")
                        
                        # 检查是否有隐藏字符
                        print(f"检查source_type中的字符码点: {' '.join([f'U+{ord(c):04X}' for c in source_type])}")
                    except Exception as update_error:
                        print(f"❌ 数据库更新失败: {update_error}")
                else:
                    print("\n✅ 测试成功: source_type正确设置为'paste'")
            else:
                print("未找到记录")
            
            conn.close()
        except Exception as e:
            print(f"查询数据库时出错: {e}")
    else:
        print(f"数据库文件不存在: {db_path}")

if __name__ == "__main__":
    test_direct_submission() 