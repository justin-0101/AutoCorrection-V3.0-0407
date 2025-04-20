#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import json
import base64

r = redis.Redis()

# 检查队列长度
print('队列长度:', r.llen('celery'))

# 查找最新的任务
tasks = r.lrange('celery', 0, 0)
if tasks:
    task_data = json.loads(tasks[0])
    body = task_data.get('body', '')
    if body:
        try:
            decoded_body = base64.b64decode(body).decode('utf-8')
            task_info = json.loads(decoded_body)
            print('最新任务ID:', task_data['headers']['id'])
            print('最新任务类型:', task_data['headers']['task'])
            print('任务参数:', task_data['headers']['argsrepr'])
        except Exception as e:
            print(f'解析任务数据出错: {e}')

# 检查错误记录
error_keys = r.keys('*error*')
print('错误记录数量:', len(error_keys))
for key in error_keys:
    try:
        value = r.get(key)
        if value:
            print(f'{key.decode("utf-8")}: {value.decode("utf-8")}')
    except Exception as e:
        print(f'读取错误记录失败: {e}')

# 检查任务结果
result_keys = r.keys('celery-task-meta-*')
print('结果记录数量:', len(result_keys))
for key in result_keys[:5]:  # 只显示前5个结果
    try:
        value = r.get(key)
        if value:
            print(f'{key.decode("utf-8")}: {value.decode("utf-8")}')
    except Exception as e:
        print(f'读取任务结果失败: {e}')

# 检查celery状态
print('Celery 状态:')
for key in r.keys('celery*'):
    try:
        if key != b'celery':  # 排除任务队列
            value_type = r.type(key)
            print(f'{key.decode("utf-8")} (类型: {value_type.decode("utf-8")})')
            if value_type == b'string':
                value = r.get(key)
                print(f'  值: {value.decode("utf-8")[:100]}...' if len(value) > 100 else f'  值: {value.decode("utf-8")}')
    except Exception as e:
        print(f'读取Celery状态失败: {e}') 