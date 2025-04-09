#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动Celery Workers
简化的脚本，仅负责启动Celery Workers
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
os.chdir(ROOT_DIR)

def start_celery_worker(queue, node_index=0, concurrency=1):
    """启动Celery Worker"""
    print(f"正在启动Celery Worker ({queue})...")
    
    # 添加索引来确保节点名称唯一
    node_name = f'worker.{queue}{node_index}@%h'
    
    cmd = [
        'celery',
        '-A', 'app.tasks:celery',
        'worker',
        '--loglevel=info',
        '--concurrency', str(concurrency),
        '-Q', queue,
        '-n', node_name
    ]
    
    try:
        # 启动Worker进程
        process = subprocess.Popen(cmd)
        print(f"Celery Worker ({queue}) 已启动")
        return process
    except Exception as e:
        print(f"启动Celery Worker ({queue}) 失败: {str(e)}")
        return None

def start_celery_beat():
    """启动Celery Beat调度器"""
    print("正在启动Celery Beat调度器...")
    
    cmd = [
        'celery',
        '-A', 'app.tasks:celery',
        'beat',
        '--loglevel=info'
    ]
    
    try:
        # 启动Beat进程
        process = subprocess.Popen(cmd)
        print("Celery Beat调度器已启动")
        return process
    except Exception as e:
        print(f"启动Celery Beat调度器失败: {str(e)}")
        return None

def main():
    """启动Celery Workers和Beat调度器"""
    print("启动Celery服务...")
    
    processes = []
    
    # 启动各队列的Worker
    worker_corrections = start_celery_worker('corrections', 0, 1)
    if worker_corrections:
        processes.append(worker_corrections)
    
    # 给各进程启动时间，避免冲突
    time.sleep(2)
    
    worker_default = start_celery_worker('default', 0, 1)
    if worker_default:
        processes.append(worker_default)
    
    time.sleep(2)
    
    # 启动Beat调度器
    beat = start_celery_beat()
    if beat:
        processes.append(beat)
    
    print("\nCelery服务已启动")
    print("按Ctrl+C停止所有服务")
    
    try:
        # 等待所有进程结束
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n正在停止Celery服务...")
        for process in processes:
            process.terminate()
        print("Celery服务已停止")

if __name__ == '__main__':
    main() 