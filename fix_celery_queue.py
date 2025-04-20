#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复Celery队列问题
将任务从默认队列移动到correction队列
"""

import redis
import json
import logging
import time
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    # 连接Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # 检查默认队列
    default_queue = 'celery'
    correction_queue = 'correction'
    
    # 获取默认队列长度
    default_queue_len = r.llen(default_queue)
    logger.info(f"默认队列({default_queue})中有 {default_queue_len} 个任务")
    
    # 获取correction队列长度
    correction_queue_len = r.llen(correction_queue)
    logger.info(f"批改队列({correction_queue})中有 {correction_queue_len} 个任务")
    
    # 如果默认队列为空，则不需要处理
    if default_queue_len == 0:
        logger.info("默认队列为空，无需处理")
        return
    
    # 从默认队列中获取所有任务
    tasks = []
    for i in range(default_queue_len):
        task = r.lindex(default_queue, i)
        if task:
            tasks.append(task)
    
    logger.info(f"从默认队列获取了 {len(tasks)} 个任务")
    
    # 检查任务并移动到correction队列
    moved_count = 0
    correction_tasks = []
    
    for task in tasks:
        try:
            # 解析任务数据
            task_data = json.loads(task)
            
            # 检查是否是批改任务
            task_name = task_data.get('headers', {}).get('task', '')
            if 'process_essay_correction' in task_name:
                logger.info(f"找到批改任务: {task_name}")
                correction_tasks.append(task)
                moved_count += 1
        except json.JSONDecodeError:
            logger.warning(f"无法解析任务数据: {task}")
        except Exception as e:
            logger.error(f"处理任务时出错: {str(e)}")
    
    logger.info(f"找到 {moved_count} 个需要移动的批改任务")
    
    # 询问用户是否确认移动
    if moved_count > 0:
        print(f"找到 {moved_count} 个需要移动的批改任务")
        confirm = input("是否将这些任务移动到correction队列? (y/n): ")
        
        if confirm.lower() == 'y':
            # 移动任务到correction队列
            moved_success = 0
            for task in correction_tasks:
                try:
                    # 从默认队列移除任务
                    r.lrem(default_queue, 1, task)
                    # 添加到correction队列
                    r.rpush(correction_queue, task)
                    moved_success += 1
                    logger.info(f"成功移动任务到correction队列")
                except Exception as e:
                    logger.error(f"移动任务时出错: {str(e)}")
            
            logger.info(f"成功移动 {moved_success}/{moved_count} 个任务到correction队列")
            print(f"成功移动 {moved_success}/{moved_count} 个任务到correction队列")
        else:
            logger.info("用户取消了任务移动操作")
            print("已取消任务移动操作")
    
    # 重启Celery工作进程
    restart = input("是否需要重启Celery工作进程? (y/n): ")
    if restart.lower() == 'y':
        logger.info("准备重启Celery工作进程")
        print("正在重启Celery工作进程...")
        
        try:
            # 关闭现有Celery进程
            import os
            os.system("taskkill /F /FI \"WINDOWTITLE eq Celery*\" /T > nul 2>&1")
            logger.info("已关闭现有Celery进程")
            print("已关闭现有Celery进程，等待3秒...")
            time.sleep(3)
            
            # 启动新的Celery工作进程
            import subprocess
            worker_cmd = (
                "start \"Celery Correction Worker\" cmd /k "
                "\"call .venv\\Scripts\\activate.bat && "
                "celery -A app.tasks.celery_app:celery_app worker --loglevel=info "
                "-P eventlet -c 10 -Q correction -n worker_correction_%time:~0,2%%time:~3,2%@%%h\""
            )
            subprocess.Popen(worker_cmd, shell=True)
            
            logger.info("已启动新的Celery工作进程")
            print("已启动新的Celery工作进程")
        except Exception as e:
            logger.error(f"重启Celery工作进程时出错: {str(e)}")
            print(f"重启Celery工作进程时出错: {str(e)}")

if __name__ == "__main__":
    print("===== Celery队列修复工具 =====")
    main()
    print("操作完成！") 