import requests

def test_login_and_submit():
    # 创建一个会话，保持cookies
    session = requests.Session()
    
    # 先获取登录页面，获取任何CSRF token
    login_page = session.get("http://localhost:5000/login")
    print(f"获取登录页面状态码: {login_page.status_code}")
    
    # 登录
    login_data = {
        "username": "admin",  # 替换为实际用户名
        "password": "admin123",  # 替换为实际密码
    }
    login_response = session.post("http://localhost:5000/login", data=login_data)
    print(f"登录响应状态码: {login_response.status_code}")
    print(f"登录后重定向URL: {login_response.url}")
    
    # 提交作文 - 测试paste类型
    correction_data = {
        "article": "这是测试PASTE类型的作文，应该将source_type设置为paste类型。",
        "subject": "测试PASTE类型",
        "source_type": "paste"  # 明确设置source_type
    }
    
    correction_response = session.post("http://localhost:5000/correction", data=correction_data)
    print(f"作文提交响应状态码: {correction_response.status_code}")
    print(f"作文提交后重定向URL: {correction_response.url}")
    print("请检查数据库中最新作文的source_type是否为'paste'")
    
if __name__ == "__main__":
    test_login_and_submit() 