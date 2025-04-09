#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Celery工作进程启动脚本
用于启动异步任务处理工作进程
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

def start_worker(queue='default', concurrency=2, loglevel='info', index=0):
    """
    启动Celery工作进程
    
    Args:
        queue: 队列名称，默认为default
        concurrency: 并发数，默认为2
        loglevel: 日志级别，默认为info
        index: worker索引，用于确保节点名称唯一
    """
    os.chdir(ROOT_DIR)
    # 添加索引来确保节点名称唯一
    node_name = f'worker.{queue}{index}@%h' if index > 0 else f'worker.{queue}@%h'
    
    cmd = [
        'celery', '-A', 'app.tasks:celery', 'worker',
        '--loglevel', loglevel,
        '--concurrency', str(concurrency),
        '-Q', queue,
        '-n', node_name
    ]
    
    print(f"启动Celery工作进程: {' '.join(cmd)}")
    process = subprocess.Popen(cmd)
    return process

def start_beat():
    """启动Celery定时任务调度器"""
    os.chdir(ROOT_DIR)
    cmd = [
        'celery', '-A', 'app.tasks:celery', 'beat',
        '--loglevel', 'info'
    ]
    
    print(f"启动Celery定时任务调度器: {' '.join(cmd)}")
    process = subprocess.Popen(cmd)
    return process

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动Celery工作进程')
    parser.add_argument('--all', action='store_true', help='启动所有工作进程')
    parser.add_argument('--corrections', action='store_true', help='启动作文批改工作进程')
    parser.add_argument('--users', action='store_true', help='启动用户管理工作进程')
    parser.add_argument('--default', action='store_true', help='启动默认工作进程')
    parser.add_argument('--beat', action='store_true', help='启动定时任务调度器')
    parser.add_argument('--concurrency', type=int, default=2, help='每个工作进程的并发数')
    parser.add_argument('--loglevel', type=str, default='info', help='日志级别')
    parser.add_argument('--count', type=int, default=1, help='每个队列启动的worker数量')
    
    args = parser.parse_args()
    processes = []
    
    # 如果没有指定具体队列，则启动所有
    if not any([args.corrections, args.users, args.default, args.beat]):
        args.all = True
    
    if args.all or args.default:
        for i in range(args.count):
            processes.append(start_worker('default', args.concurrency, args.loglevel, i))
    
    if args.all or args.corrections:
        for i in range(args.count):
            processes.append(start_worker('corrections', args.concurrency, args.loglevel, i))
    
    if args.all or args.users:
        for i in range(args.count):
            processes.append(start_worker('users', args.concurrency, args.loglevel, i))
    
    if args.all or args.beat:
        processes.append(start_beat())
    
    # 等待所有进程结束
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n正在关闭工作进程...")
        for process in processes:
            process.terminate()
        
        print("工作进程已关闭")

if __name__ == '__main__':
    main() 