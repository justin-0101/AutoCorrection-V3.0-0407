from flask import Flask, session, redirect, url_for, request
import os

app = Flask(__name__)
app.secret_key = 'debug_key'  # 用于测试的密钥

@app.route('/')
def test_index():
    if 'user_id' in session:
        return f'''
        <h1>测试页面</h1>
        <p>当前会话状态:</p>
        <ul>
            <li>用户ID: {session.get('user_id')}</li>
            <li>用户名: {session.get('username')}</li>
            <li>角色: {session.get('role')}</li>
        </ul>
        <p><a href="/simulate_admin">模拟admin登录</a></p>
        <p><a href="/simulate_user">模拟普通用户登录</a></p>
        <p><a href="/admin_test">访问管理后台测试</a></p>
        <p><a href="/clear">清除会话</a></p>
        '''
    else:
        return '''
        <h1>未登录状态</h1>
        <p><a href="/simulate_admin">模拟admin登录</a></p>
        <p><a href="/simulate_user">模拟普通用户登录</a></p>
        '''

@app.route('/simulate_admin')
def simulate_admin():
    session['user_id'] = 1
    session['username'] = 'juschen'
    session['role'] = 'admin'
    return redirect('/')

@app.route('/simulate_user')
def simulate_user():
    session['user_id'] = 1
    session['username'] = 'juschen'
    session['role'] = 'user'
    return redirect('/')

@app.route('/admin_test')
def admin_test():
    if 'user_id' not in session:
        return '请先登录', 401
    
    role = session.get('role')
    if role != 'admin':
        return '您没有权限访问管理后台', 403
    
    return '''
    <h1>管理后台模拟页面</h1>
    <p>如果您看到这个页面，说明session能正确识别admin角色</p>
    <p>这意味着您在真实应用中应该能够访问管理后台</p>
    <p>建议检查：</p>
    <ol>
        <li>退出登录并重新登录系统</li>
        <li>确认URL是否正确：/admin/dashboard</li>
        <li>检查app.py文件是否有错误导致断点或异常</li>
    </ol>
    <p><a href="/">返回测试首页</a></p>
    '''

@app.route('/clear')
def clear_session():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    # 打印当前运行的目录，确认在项目根目录下
    print(f"当前工作目录: {os.getcwd()}")
    print("测试服务器启动在: http://127.0.0.1:5001")
    print("请访问上述地址测试session处理")
    app.run(debug=True, port=5001) 