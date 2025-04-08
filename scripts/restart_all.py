#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统完全重启脚本
清理缓存并重新启动所有服务
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

def clear_cache():
    """
    清理Python缓存文件
    """
    print("正在清理Python缓存文件...")
    
    # 找到所有的__pycache__目录
    for root, dirs, files in os.walk(ROOT_DIR):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                cache_dir = os.path.join(root, dir_name)
                print(f"删除缓存目录: {cache_dir}")
                try:
                    shutil.rmtree(cache_dir)
                except Exception as e:
                    print(f"无法删除 {cache_dir}: {str(e)}")
    
    # 删除.pyc文件
    for root, dirs, files in os.walk(ROOT_DIR):
        for file in files:
            if file.endswith(".pyc"):
                pyc_file = os.path.join(root, file)
                print(f"删除缓存文件: {pyc_file}")
                try:
                    os.remove(pyc_file)
                except Exception as e:
                    print(f"无法删除 {pyc_file}: {str(e)}")
    
    print("缓存清理完成")

def kill_all_processes():
    """
    结束所有相关进程
    """
    print("正在终止所有相关进程...")
    
    if os.name == 'nt':  # Windows
        # 结束Python进程
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        # 结束Redis进程
        subprocess.run(['taskkill', '/F', '/IM', 'redis-server.exe'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        # 结束Celery进程
        subprocess.run(['taskkill', '/F', '/IM', 'celery.exe'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    else:  # Linux/Mac
        # 结束Python进程
        subprocess.run(['pkill', '-9', '-f', 'python'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        # 结束Redis进程
        subprocess.run(['pkill', '-9', '-f', 'redis-server'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        # 结束Celery进程
        subprocess.run(['pkill', '-9', '-f', 'celery'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    
    print("所有进程已终止")
    time.sleep(2)  # 给进程时间完全终止

def start_redis():
    """
    启动Redis服务器
    """
    print("正在启动Redis服务器...")
    
    os.chdir(ROOT_DIR)
    
    if os.path.exists('redis.conf'):
        cmd = ['redis-server', 'redis.conf']
    else:
        cmd = ['redis-server']
    
    process = subprocess.Popen(cmd, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
    
    print("Redis服务器已启动")
    time.sleep(2)  # 给Redis启动时间
    
    return process

def start_celery_workers():
    """
    启动Celery workers
    """
    print("正在启动Celery workers...")
    
    os.chdir(ROOT_DIR)
    
    # 启动corrections队列的worker（唯一节点名称）
    corrections_worker = subprocess.Popen([
        'celery', '-A', 'tasks.celery_app:celery_app', 'worker',
        '--loglevel', 'info',
        '--concurrency', '1',
        '-Q', 'corrections',
        '-n', 'worker.corrections1@%h'
    ])
    
    time.sleep(2)  # 间隔启动，避免冲突
    
    # 启动默认队列的worker（唯一节点名称）
    default_worker = subprocess.Popen([
        'celery', '-A', 'tasks.celery_app:celery_app', 'worker',
        '--loglevel', 'info',
        '--concurrency', '1',
        '-Q', 'default',
        '-n', 'worker.default1@%h'
    ])
    
    time.sleep(2)  # 间隔启动，避免冲突
    
    # 启动beat调度器
    beat = subprocess.Popen([
        'celery', '-A', 'tasks.celery_app:celery_app', 'beat',
        '--loglevel', 'info'
    ])
    
    print("Celery workers和beat调度器已启动")
    
    return [corrections_worker, default_worker, beat]

def start_flask_app():
    """
    启动Flask应用
    """
    print("正在启动Flask应用...")
    
    os.chdir(ROOT_DIR)
    
    flask_app = subprocess.Popen([
        'python', 'run.py',
        '--debug'
    ])
    
    print("Flask应用已启动")
    
    return flask_app

def main():
    """主函数"""
    print("=== 系统完全重启脚本 ===")
    
    # 1. 结束所有进程
    kill_all_processes()
    
    # 2. 清理缓存
    clear_cache()
    
    # 3. 启动Redis
    redis_process = start_redis()
    
    # 4. 启动Celery workers
    worker_processes = start_celery_workers()
    
    # 5. 启动Flask应用
    flask_process = start_flask_app()
    
    print("\n所有服务已重新启动并清理缓存")
    print("您现在可以在浏览器中访问 http://127.0.0.1:5000/ 查看应用")
    print("按Ctrl+C可以停止所有服务")
    
    try:
        # 等待Flask应用退出
        flask_process.wait()
    except KeyboardInterrupt:
        print("\n正在关闭所有服务...")
        
        # 停止Flask应用
        flask_process.terminate()
        
        # 停止Celery workers
        for process in worker_processes:
            process.terminate()
        
        # 停止Redis
        redis_process.terminate()
        
        print("所有服务已关闭")

if __name__ == '__main__':
    main() 