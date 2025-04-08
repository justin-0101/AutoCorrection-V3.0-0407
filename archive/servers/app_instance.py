from flask import Flask
import os

# 创建Flask应用 - 确保只创建一次
def create_flask_app():
    # 检查是否已经创建了应用实例
    if hasattr(create_flask_app, 'app'):
        return create_flask_app.app
    
    # 创建新的应用实例
    flask_app = Flask(__name__, static_folder='static', static_url_path='/static')
    flask_app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')  # 在app.py中会从环境变量重新设置
    
    # 设置静态文件夹
    if not os.path.exists('static'):
        os.makedirs('static/css', exist_ok=True)
        os.makedirs('static/js', exist_ok=True)
    
    # 存储实例以便复用
    create_flask_app.app = flask_app
    return flask_app

# 获取应用实例
app = create_flask_app()

# 如果直接运行此文件，则输出提示
if __name__ == '__main__':
    print("这个文件不应该直接运行。请运行app.py来启动应用。") 