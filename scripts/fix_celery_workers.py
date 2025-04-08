#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复Celery工作进程节点名称重复问题
停止所有当前运行的Celery worker并用唯一节点名称重新启动它们
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

def kill_all_celery_workers():
    """
    停止所有Celery worker进程
    """
    print("正在停止所有Celery worker进程...")
    
    if os.name == 'nt':  # Windows
        # 通过taskkill命令杀死所有celery进程
        subprocess.run(['taskkill', '/F', '/IM', 'celery.exe'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        # 也杀死可能运行的Python celery进程
        subprocess.run(['taskkill', '/F', '/FI', 'IMAGENAME eq python.exe', '/FI', 'WINDOWTITLE eq *celery*'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    else:  # Linux/Mac
        # 使用pkill杀死celery进程
        subprocess.run(['pkill', '-9', '-f', 'celery'], 
                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    
    print("等待进程完全终止...")
    time.sleep(2)  # 给进程一些时间终止

def start_redis_server():
    """
    启动Redis服务器
    """
    print("正在启动Redis服务器...")
    
    os.chdir(ROOT_DIR)
    
    if os.path.exists('redis.conf'):
        # 如果存在redis.conf配置文件，使用它启动
        cmd = ['redis-server', 'redis.conf']
    else:
        # 否则使用默认配置
        cmd = ['redis-server']
    
    # 使用Popen启动后台进程
    process = subprocess.Popen(cmd, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    print("Redis服务器已启动")
    
    # 给Redis一些时间启动
    time.sleep(1)
    
    return process

def start_celery_workers():
    """
    使用唯一节点名称启动Celery worker
    """
    print("正在启动Celery workers...")
    
    os.chdir(ROOT_DIR)
    
    # 启动corrections队列的worker，确保节点名称唯一
    corrections_worker = subprocess.Popen([
        'celery', '-A', 'tasks.celery_app:celery_app', 'worker',
        '--loglevel', 'info',
        '--concurrency', '1',
        '-Q', 'corrections',
        '-n', 'worker.corrections1@%h'
    ])
    
    # 启动默认队列的worker，确保节点名称唯一
    default_worker = subprocess.Popen([
        'celery', '-A', 'tasks.celery_app:celery_app', 'worker',
        '--loglevel', 'info',
        '--concurrency', '1',
        '-Q', 'default',
        '-n', 'worker.default1@%h'
    ])
    
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
    
    # 启动Flask应用
    flask_app = subprocess.Popen([
        'python', 'run.py',
        '--debug'
    ])
    
    print("Flask应用已启动")
    
    return flask_app

def main():
    """主函数"""
    print("=== 修复Celery工作进程节点名称重复问题 ===")
    
    # 1. 停止所有Celery进程
    kill_all_celery_workers()
    
    # 2. 启动Redis服务器
    redis_process = start_redis_server()
    
    # 3. 启动Celery workers
    worker_processes = start_celery_workers()
    
    # 4. 启动Flask应用
    flask_process = start_flask_app()
    
    # 所有进程已启动
    print("\n所有服务已重新启动，具有唯一的节点名称")
    print("按Ctrl+C停止所有服务")
    
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
        
        # 停止Redis服务器
        redis_process.terminate()
        
        print("所有服务已关闭")

if __name__ == '__main__':
    main() 