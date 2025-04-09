#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简化启动脚本
启动所有必要的服务：Redis、Celery worker 和 Flask应用
"""

import os
import sys
import time
import subprocess
import atexit
import threading
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent
os.chdir(ROOT_DIR)

# 存储进程
redis_process = None
celery_process = None

def terminate_processes():
    """终止所有进程"""
    global redis_process, celery_process
    
    # 终止Celery
    if celery_process and celery_process.poll() is None:
        try:
            celery_process.terminate()
            print("Celery worker已停止")
        except Exception as e:
            print(f"停止Celery worker失败: {str(e)}")
    
    # 终止Redis
    if redis_process and redis_process.poll() is None:
        try:
            redis_process.terminate()
            print("Redis服务已停止")
        except Exception as e:
            print(f"停止Redis失败: {str(e)}")

# 注册终止函数
atexit.register(terminate_processes)

def start_redis():
    """启动Redis服务器"""
    global redis_process
    print("\n====== 启动Redis服务器 ======")
    
    # 使用本地 redis 目录中的可执行文件
    redis_server = str(ROOT_DIR / 'redis' / 'redis-server.exe')
    redis_conf = str(ROOT_DIR / 'redis.conf')
    
    if not os.path.exists(redis_server):
        print(f"Redis服务器程序不存在: {redis_server}")
        print("请确保已下载 Redis 便携版并解压到 redis 目录")
        return False
        
    try:
        redis_process = subprocess.Popen([redis_server, redis_conf])
        print("Redis服务器已启动")
        
        # 等待Redis启动
        time.sleep(2)
        return True
    except Exception as e:
        print(f"启动Redis失败: {str(e)}")
        return False

def start_celery():
    """启动Celery worker"""
    global celery_process
    print("\n====== 启动Celery Worker ======")
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT_DIR)
    
    # Windows下使用不同的命令
    if sys.platform == 'win32':
        cmd = ['celery', '-A', 'app.tasks:celery', 'worker', 
              '--pool=solo', '--loglevel=info',
              '-E',
              '--concurrency=1']
    else:
        cmd = ['celery', '-A', 'app.tasks:celery', 'worker', 
              '--loglevel=info',
              '-E',
              '--concurrency=1']
    
    try:
        celery_process = subprocess.Popen(cmd, env=env)
        print("Celery worker已启动")
        
        # 等待Celery启动
        time.sleep(3)
        return True
    except Exception as e:
        print(f"启动Celery worker失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("===== 系统启动 =====")
    
    # 1. 启动Redis
    if not start_redis():
        print("Redis启动失败，无法继续。")
        sys.exit(1)
    
    # 2. 启动Celery worker
    if not start_celery():
        print("Celery worker启动失败，无法继续。")
        terminate_processes()
        sys.exit(1)
    
    # 3. 启动Flask应用
    print("\n====== 启动Flask应用 ======")
    try:
        # 导入Flask应用
        from app import create_app
        app = create_app()
        
        # 打印应用信息
        print("所有服务已启动:")
        print("- Redis服务器正在运行")
        print("- Celery worker正在运行")
        print("- Flask应用可在 http://127.0.0.1:5000/ 访问")
        print("\n按Ctrl+C停止所有服务")
        
        # 运行Flask应用
        app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        print(f"启动Flask应用失败: {str(e)}")
        import traceback
        traceback.print_exc()
        terminate_processes()
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n正在关闭所有服务...")
        terminate_processes()
        sys.exit(0) 