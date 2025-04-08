#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统诊断脚本
检查各个组件的状态和配置
"""

import os
import sys
import socket
import subprocess
import importlib
import traceback
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent
os.chdir(ROOT_DIR)

def check_port(port, host='127.0.0.1'):
    """检查端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0  # 0表示连接成功，端口已占用
    except Exception as e:
        print(f"检查端口错误: {str(e)}")
        return False

def check_redis_connection():
    """检查Redis连接"""
    print("\n===== 检查Redis连接 =====")
    redis_running = check_port(6379)
    if redis_running:
        print("Redis服务正在运行 (端口6379已开放)")
    else:
        print("Redis服务未运行 (端口6379未开放)")
    
    try:
        # 尝试导入redis库
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0)
        ping_result = client.ping()
        print(f"Redis连接测试: {'成功' if ping_result else '失败'}")
    except ImportError:
        print("未安装Redis库，无法进行连接测试")
    except Exception as e:
        print(f"Redis连接测试失败: {str(e)}")
    
    return redis_running

def check_celery_config():
    """检查Celery配置"""
    print("\n===== 检查Celery配置 =====")
    try:
        from tasks.celery_app import celery_app
        print("成功导入Celery应用")
        print(f"Broker URL: {celery_app.conf.broker_url}")
        print(f"Result Backend: {celery_app.conf.result_backend}")
        
        # 检查任务发现
        print("已发现的任务:")
        for task_name in celery_app.tasks.keys():
            if not task_name.startswith('celery.'):
                print(f"  - {task_name}")
    except Exception as e:
        print(f"Celery配置检查失败: {str(e)}")
        traceback.print_exc()

def check_flask_app():
    """检查Flask应用"""
    print("\n===== 检查Flask应用 =====")
    try:
        from app import create_app
        app = create_app()
        
        # 检查Flask配置
        print(f"Flask应用名称: {app.name}")
        print(f"Flask调试模式: {'启用' if app.debug else '禁用'}")
        print(f"Flask密钥设置: {'已设置' if app.secret_key else '未设置'}")
        
        # 检查路由
        print("\nFlask路由列表:")
        for rule in app.url_map.iter_rules():
            print(f"  - {rule.endpoint}: {rule.rule} [{','.join(sorted(rule.methods))}]")
        
        # 检查扩展
        print("\nFlask扩展:")
        if hasattr(app, 'extensions'):
            for extension_name in app.extensions:
                print(f"  - {extension_name}")
        else:
            print("  没有已注册的扩展")
    except Exception as e:
        print(f"Flask应用检查失败: {str(e)}")
        traceback.print_exc()

def check_running_services():
    """检查正在运行的服务"""
    print("\n===== 检查正在运行的服务 =====")
    
    # 检查是否有Redis进程
    redis_running = False
    
    # 检查是否有Celery进程
    celery_running = False
    
    # 检查是否有Flask进程
    flask_running = False
    
    # 使用不同的方法根据操作系统检查
    if os.name == 'nt':  # Windows
        try:
            # 检查Redis
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq redis-server.exe'], 
                                    capture_output=True, text=True)
            redis_running = 'redis-server.exe' in result.stdout
            
            # 检查Celery/Python进程
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                                    capture_output=True, text=True)
            
            # 简单检查，可能不够准确
            celery_running = 'python.exe' in result.stdout
            flask_running = check_port(5000)
        except Exception as e:
            print(f"检查Windows进程时出错: {str(e)}")
    else:  # Linux/Mac
        try:
            # 检查Redis
            result = subprocess.run(['pgrep', 'redis-server'], 
                                    capture_output=True, text=True)
            redis_running = result.stdout.strip() != ''
            
            # 检查Celery
            result = subprocess.run(['pgrep', '-f', 'celery'], 
                                    capture_output=True, text=True)
            celery_running = result.stdout.strip() != ''
            
            # 检查Flask(通常是Python进程运行Flask)
            flask_running = check_port(5000)
        except Exception as e:
            print(f"检查Unix进程时出错: {str(e)}")
    
    print(f"Redis服务状态: {'运行中' if redis_running else '未运行'}")
    print(f"Celery服务状态: {'运行中' if celery_running else '未运行'}")
    print(f"Flask应用状态: {'运行中' if flask_running else '未运行'}")
    
    return {
        'redis': redis_running,
        'celery': celery_running,
        'flask': flask_running
    }

def check_database():
    """检查数据库连接"""
    print("\n===== 检查数据库连接 =====")
    try:
        # 导入数据库模型
        from app.models.db import db
        from app import create_app
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            # 检查数据库连接
            engine = db.engine
            connection = engine.connect()
            connection.close()
            
            print(f"数据库连接成功")
            print(f"数据库URL: {engine.url}")
            print(f"数据库驱动: {engine.driver}")
    except Exception as e:
        print(f"数据库连接检查失败: {str(e)}")
        traceback.print_exc()

def main():
    """主函数"""
    print("=== 系统诊断工具 ===")
    
    # 检查Python版本和工作目录
    print(f"Python版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    
    # 检查关键组件
    redis_status = check_redis_connection()
    check_celery_config()
    check_flask_app()
    running_services = check_running_services()
    check_database()
    
    # 总结
    print("\n===== 诊断总结 =====")
    if not redis_status:
        print("❌ Redis未运行，这将导致Celery无法正常工作")
    
    if not running_services['flask']:
        print("❌ Flask应用未运行，访问网站将显示连接被拒绝")
    
    print("\n如需启动所有服务，请运行:")
    print("python run_all_services.py")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"诊断过程中出错: {str(e)}")
        traceback.print_exc() 