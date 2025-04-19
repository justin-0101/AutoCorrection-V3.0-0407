#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
改进的Celery启动脚本
确保使用eventlet作为worker池，并应用猴子补丁
"""

# 设置环境变量并在导入其他模块前应用猴子补丁
import os
os.environ['CELERY_WORKER_POOL'] = 'eventlet'

try:
    import eventlet
    eventlet.monkey_patch()
    print("eventlet猴子补丁已成功应用")
except ImportError:
    print("警告: 未安装eventlet，请执行 pip install eventlet")
except Exception as e:
    print(f"应用eventlet猴子补丁失败: {str(e)}")

import sys
import argparse
import subprocess
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

def start_celery_worker(queue='correction', concurrency=10, loglevel='info', pool='eventlet'):
    """
    启动Celery工作进程
    
    Args:
        queue: 队列名称，默认为correction
        concurrency: 并发数，默认为10
        loglevel: 日志级别，默认为info
        pool: 使用的池，默认为eventlet
    """
    os.chdir(ROOT_DIR)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    node_name = f'worker_{queue}_{timestamp}@%h'
    
    # 构建命令 (使用正确的应用路径)
    cmd = [
        'celery', 
        '-A', 'app.tasks.celery_app:celery_app', 
        'worker',
        '--loglevel', loglevel,
        '-P', pool,
        '-c', str(concurrency),
        '-Q', queue,
        '-n', node_name
    ]
    
    print(f"启动Celery工作进程: {' '.join(cmd)}")
    return subprocess.Popen(cmd)

def start_celery_beat(loglevel='info'):
    """
    启动Celery Beat调度器
    
    Args:
        loglevel: 日志级别，默认为info
    """
    os.chdir(ROOT_DIR)
    
    # 构建命令 (使用正确的应用路径)
    cmd = [
        'celery', 
        '-A', 'app.tasks.celery_app:celery_app', 
        'beat',
        '--loglevel', loglevel
    ]
    
    print(f"启动Celery Beat调度器: {' '.join(cmd)}")
    return subprocess.Popen(cmd)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动Celery工作进程和Beat调度器')
    parser.add_argument('--queue', type=str, default='correction', help='要处理的队列名称')
    parser.add_argument('--concurrency', type=int, default=10, help='并发数')
    parser.add_argument('--loglevel', type=str, default='info', help='日志级别')
    parser.add_argument('--pool', type=str, default='eventlet', help='Worker池类型')
    parser.add_argument('--beat', action='store_true', help='是否启动Beat调度器')
    
    args = parser.parse_args()
    processes = []
    
    # 启动Worker
    worker_process = start_celery_worker(
        queue=args.queue,
        concurrency=args.concurrency,
        loglevel=args.loglevel,
        pool=args.pool
    )
    processes.append(worker_process)
    
    # 如果需要，启动Beat
    if args.beat:
        beat_process = start_celery_beat(loglevel=args.loglevel)
        processes.append(beat_process)
    
    # 等待进程结束
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n正在关闭进程...")
        for process in processes:
            try:
                process.terminate()
            except:
                pass
        print("所有进程已关闭")

if __name__ == '__main__':
    main() 