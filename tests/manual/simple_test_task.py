#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单Celery任务测试脚本
用于测试Celery worker是否正常工作
"""

from celery import Celery
import time

# 初始化Celery实例
app = Celery('simple_test',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0')

@app.task
def add(x, y):
    """简单的加法任务"""
    print(f"执行加法: {x} + {y}")
    return x + y

if __name__ == "__main__":
    print("提交简单测试任务...")
    result = add.delay(4, 4)
    print(f"任务ID: {result.id}")
    
    # 等待任务完成
    print("等待任务完成...")
    for _ in range(10):
        print(f"任务状态: {result.state}")
        if result.ready():
            break
        time.sleep(1)
    
    if result.ready():
        if result.successful():
            print(f"任务成功! 结果: {result.get()}")
        else:
            print(f"任务失败: {result.traceback}")
    else:
        print("任务未完成") 