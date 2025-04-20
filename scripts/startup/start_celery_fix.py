#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复的Celery启动脚本
确保在Windows环境下也能正确应用Eventlet猴子补丁
"""

import os
import sys
import subprocess
from pathlib import Path
import time
from datetime import datetime

# 获取项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(ROOT_DIR)

def start_celery_worker():
    """启动Celery worker使用新的模块加载方式"""
    print("正在启动Celery worker...")
    
    # 生成包含时间戳的唯一worker名称
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    node_name = f"worker_correction_{timestamp}@%h"
    
    # 构建命令行
    cmd = [
        sys.executable,  # 使用当前Python解释器
        "-m", "celery",  # 以模块方式启动celery
        "-A", "app.tasks.celery_app:celery_app",
        "worker",
        "--loglevel=info",
        "-P", "eventlet",
        "-c", "10",
        "-Q", "correction",
        "-n", node_name
    ]
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    
    # 启动进程
    print(f"执行命令: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        env=env,
        cwd=str(ROOT_DIR)
    )
    
    return process

if __name__ == "__main__":
    print("===== 修复的Celery启动脚本 =====")
    
    # 检查虚拟环境是否激活
    if not os.path.exists(".venv/Scripts/activate.bat"):
        print("警告: 未找到虚拟环境，请确保已激活虚拟环境")
    
    # 启动worker
    worker = start_celery_worker()
    
    print("Celery worker已启动!")
    print("按 Ctrl+C 停止...")
    
    try:
        # 保持脚本运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止Celery worker...")
        worker.terminate()
        print("Celery worker已停止") 