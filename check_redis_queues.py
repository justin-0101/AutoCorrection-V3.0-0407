#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis队列检查工具
用于检查Redis中Celery任务队列的状态
"""

import redis
import json
from app.config import Config

def check_redis_queues():
    """检查Redis中的Celery队列"""
    try:
        # 连接到Redis
        broker_url = Config.CELERY_BROKER_URL
        print(f"连接到Redis: {broker_url}")
        
        # 分析URL获取连接参数
        if broker_url.startswith('redis://'):
            # 格式: redis://[:password@]host[:port][/db]
            url_parts = broker_url.replace('redis://', '').split('@')
            if len(url_parts) > 1:
                password = url_parts[0]
                host_port_db = url_parts[1]
            else:
                password = None
                host_port_db = url_parts[0]
            
            host_port, *db_parts = host_port_db.split('/')
            db = int(db_parts[0]) if db_parts else 0
            
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 6379
        else:
            print(f"不支持的URL格式: {broker_url}")
            return
        
        # 创建Redis客户端
        r = redis.Redis(
            host=host, 
            port=port, 
            password=password, 
            db=db,
            decode_responses=True  # 解码响应为字符串
        )
        
        # 检查连接
        if r.ping():
            print("成功连接到Redis服务器")
        else:
            print("无法连接到Redis服务器")
            return
        
        # 获取所有键
        all_keys = r.keys('*')
        print(f"\n找到 {len(all_keys)} 个键")
        
        # 查找Celery队列键
        celery_queues = sorted([k for k in all_keys if k.startswith('celery:') and not k.startswith('celery-task-meta-')])
        meta_keys = sorted([k for k in all_keys if k.startswith('celery-task-meta-')])
        
        # 显示队列情况
        print(f"\n找到 {len(celery_queues)} 个Celery队列:")
        
        for key in celery_queues:
            # 获取键的类型
            key_type = r.type(key)
            
            if key_type == 'list':
                # 如果是列表（队列），获取长度和内容
                queue_len = r.llen(key)
                print(f"\n队列: {key} (类型: {key_type}, 长度: {queue_len})")
                
                if queue_len > 0:
                    # 显示队列中的任务（最多5个）
                    tasks = r.lrange(key, 0, min(4, queue_len-1))
                    print("  任务预览:")
                    for i, task in enumerate(tasks):
                        # 限制任务内容显示长度
                        preview = task[:200] + '...' if len(task) > 200 else task
                        print(f"  [{i}] {preview}")
                    
                    if queue_len > 5:
                        print(f"  ... 还有 {queue_len - 5} 个任务未显示")
            else:
                # 其他类型的键
                print(f"\n键: {key} (类型: {key_type})")
                
                if key_type == 'hash':
                    # 如果是哈希，显示字段
                    fields = r.hkeys(key)
                    print(f"  包含 {len(fields)} 个字段")
                    if len(fields) > 0:
                        print("  字段预览:", ', '.join(fields[:5]))
                        if len(fields) > 5:
                            print(f"  ... 还有 {len(fields) - 5} 个字段未显示")
        
        # 显示任务元数据
        print(f"\n找到 {len(meta_keys)} 个任务元数据记录:")
        
        for i, key in enumerate(meta_keys[:10]):  # 最多显示10个
            value = r.get(key)
            task_id = key.replace('celery-task-meta-', '')
            
            try:
                # 尝试解析任务元数据
                meta = json.loads(value)
                status = meta.get('status', 'UNKNOWN')
                
                print(f"\n任务元数据 {i+1}/{len(meta_keys)}: {task_id}")
                print(f"  状态: {status}")
                
                if status == 'SUCCESS':
                    result = meta.get('result')
                    print(f"  结果: {result}")
                elif status == 'FAILURE':
                    error = meta.get('traceback')
                    print(f"  错误: {meta.get('exception')}")
                    if error:
                        # 显示错误的前几行
                        error_lines = error.split('\n')
                        print("  错误详情:")
                        for line in error_lines[:5]:
                            print(f"    {line}")
                        if len(error_lines) > 5:
                            print(f"    ... 还有 {len(error_lines) - 5} 行未显示")
            except json.JSONDecodeError:
                print(f"\n任务元数据 {i+1}/{len(meta_keys)}: {task_id}")
                print("  无法解析元数据内容")
                print(f"  原始内容: {value[:100]}")
        
        if len(meta_keys) > 10:
            print(f"\n... 还有 {len(meta_keys) - 10} 条任务元数据记录未显示")
            
        # 检查我们的测试任务
        test_tasks = [
            '62932a96-e18e-4739-af1d-662358a82694',  # 通知任务
            '25e20fe1-dc4f-42b2-b853-2586c223b048'   # 监控任务
        ]
        
        print("\n检查最近提交的测试任务:")
        for task_id in test_tasks:
            meta_key = f'celery-task-meta-{task_id}'
            value = r.get(meta_key)
            
            if value:
                try:
                    meta = json.loads(value)
                    print(f"\n任务ID: {task_id}")
                    print(f"  状态: {meta.get('status', 'UNKNOWN')}")
                    
                    if meta.get('status') == 'SUCCESS':
                        print(f"  结果: {meta.get('result')}")
                    elif meta.get('status') == 'FAILURE':
                        print(f"  错误: {meta.get('exception')}")
                        if meta.get('traceback'):
                            print("  错误详情的前几行:")
                            error_lines = meta.get('traceback').split('\n')
                            for line in error_lines[:5]:
                                print(f"    {line}")
                except Exception as e:
                    print(f"  解析元数据时出错: {str(e)}")
            else:
                # 尝试检查队列里是否有此任务
                print(f"\n任务ID: {task_id}")
                print("  元数据不存在，检查队列...")
                
                found = False
                for queue_key in celery_queues:
                    if r.type(queue_key) == 'list':
                        queue_content = r.lrange(queue_key, 0, -1)
                        for item in queue_content:
                            if task_id in item:
                                print(f"  找到任务在队列 {queue_key} 中")
                                found = True
                                break
                
                if not found:
                    print("  任务在Redis中不存在，可能已过期或未提交成功")
        
        # 清理连接
        r.close()
        
    except Exception as e:
        print(f"检查Redis队列时出错: {str(e)}")

if __name__ == "__main__":
    check_redis_queues() 