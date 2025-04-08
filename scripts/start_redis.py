#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动Redis服务器
简化的脚本，仅负责启动Redis服务器
"""

import os
import sys
import subprocess
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
os.chdir(ROOT_DIR)

def start_redis():
    """启动Redis服务器"""
    print("正在启动Redis服务器...")
    
    # 检查redis.conf是否存在
    if os.path.exists('redis.conf'):
        cmd = ['redis-server', 'redis.conf']
        print("使用配置文件: redis.conf")
    else:
        cmd = ['redis-server']
        print("使用默认配置")
    
    try:
        # 启动Redis进程
        process = subprocess.Popen(cmd)
        
        print("Redis服务器已启动")
        print("按Ctrl+C停止服务器")
        
        # 等待进程结束
        process.wait()
    except KeyboardInterrupt:
        print("\n正在停止Redis服务器...")
        process.terminate()
        print("Redis服务器已停止")
    except Exception as e:
        print(f"启动Redis失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    start_redis() 