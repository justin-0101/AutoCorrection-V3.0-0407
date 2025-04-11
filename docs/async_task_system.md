# 异步任务系统设计

## 1. 概述

异步任务系统是作文批改平台的核心基础架构，负责处理耗时操作如作文批改、邮件发送、数据分析等，使系统能够高效处理并发请求。本文档详细描述了异步任务系统的架构设计和实现方案。

## 2. 系统架构

### 2.1 组件构成

异步任务系统主要由以下组件构成：

1. **Celery应用**：负责任务定义、调度和执行
2. **消息代理（Redis）**：传递任务消息
3. **结果后端（Redis）**：存储任务结果
4. **任务队列**：不同类型的任务分配到不同队列
5. **Worker进程**：执行具体任务
6. **定时任务调度器（Beat）**：处理周期性任务

### 2.2 架构图

```
┌─────────────────┐     ┌─────────────────┐
│  Web应用（API） │────►│  Celery应用      │
└─────────────────┘     └────────┬────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │  消息代理(Redis) │
         │              └────────┬────────┘
         │                       │
         │                       │
┌────────▼────────┐     ┌────────▼────────┐
│ WebSocket服务   │     │  Worker进程      │
└─────────────────┘     └────────┬────────┘
         ▲                       │
         │                       ▼
         │              ┌─────────────────┐
         └──────────────┤  结果后端(Redis) │
                        └─────────────────┘
```

## 3. 配置设计

### 3.1 Celery配置

```python
# config/celery_config.py
"""
Celery配置模块
定义任务队列的各项配置
"""
import os
from datetime import timedelta

# 消息代理设置
broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# 序列化设置
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
enable_utc = True

# 任务设置
task_acks_late = True
task_reject_on_worker_lost = True
task_track_started = True
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 500

# 结果设置
result_expires = 60 * 60 * 24  # 1 day

# 配置任务队列
task_queues = {
    'default': {'exchange': 'default', 'routing_key': 'default'},
    'correction': {'exchange': 'correction', 'routing_key': 'correction.tasks'},
    'users': {'exchange': 'users', 'routing_key': 'user.tasks'}
}

# 默认队列
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'

# 任务路由
task_routes = {
    'tasks.correction_tasks.*': {'queue': 'correction'},
    'tasks.user_tasks.*': {'queue': 'users'},
}

# 定时任务
beat_schedule = {
    'reset-monthly-essay-count': {
        'task': 'tasks.user_tasks.reset_monthly_essay_count',
        'schedule': timedelta(days=1),  # 每天检查一次
        'options': {'queue': 'users'}
    }
}

# 将所有配置导出为一个字典
CELERY_CONFIG = {
    'broker_url': broker_url,
    'result_backend': result_backend,
    'task_serializer': task_serializer,
    'result_serializer': result_serializer,
    'accept_content': accept_content,
    'timezone': timezone,
    'enable_utc': enable_utc,
    'task_acks_late': task_acks_late,
    'task_reject_on_worker_lost': task_reject_on_worker_lost,
    'task_track_started': task_track_started,
    'worker_prefetch_multiplier': worker_prefetch_multiplier,
    'worker_max_tasks_per_child': worker_max_tasks_per_child,
    'result_expires': result_expires,
    'task_queues': task_queues,
    'task_default_queue': task_default_queue,
    'task_default_exchange': task_default_exchange,
    'task_default_routing_key': task_default_routing_key,
    'task_routes': task_routes,
    'beat_schedule': beat_schedule,
}
```

### 3.2 Celery应用初始化

```python
# tasks/celery_app.py
"""
Celery应用配置
配置异步任务队列
"""
import os
from celery import Celery
from pathlib import Path
import sys
from dotenv import load_dotenv

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 加载环境变量
load_dotenv(os.path.join(ROOT_DIR, '.env'))

# 导入配置
from config.celery_config import CELERY_CONFIG

# 创建Celery应用
celery_app = Celery('autocorrection')

# 配置Celery
celery_app.conf.update(CELERY_CONFIG)

# 自动发现任务
celery_app.autodiscover_tasks(['tasks.correction_tasks', 'tasks.user_tasks'])

# 这里可以定义一些基础任务
@celery_app.task(bind=True)
def debug_task(self):
    """用于测试Celery是否正常工作的任务"""
    print(f'Request: {self.request!r}')
    return 'Celery worker is alive!'
```

## 4. 任务模块设计

### 4.1 作文批改任务

```python
# tasks/correction_tasks.py
@shared_task(
    name='tasks.correction_tasks.process_essay_correction',
    bind=True,
    max_retries=3,
    default_retry_delay=5*60,  # 5分钟后重试
    acks_late=True
)
def process_essay_correction(self, essay_id, title, content, user_id=None, grade=None):
    """
    异步处理作文批改任务
    
    Args:
        self: Celery任务实例
        essay_id: 作文ID
        title: 作文标题
        content: 作文内容
        user_id: 用户ID（可选）
        grade: 年级（可选）
        
    Returns:
        dict: 批改结果
    """
    start_time = time.time()
    logger.info(f"开始异步批改作文，ID: {essay_id}")
    
    try:
        # 更新作文状态为处理中
        update_essay_status(essay_id, "processing")
        
        # 创建AI服务实例
        ai_service = AIService()
        
        # 批改作文
        correction_result = ai_service.correct_essay(
            essay_text=content,
            title=title,
            grade=grade
        )
        
        # 检查批改是否成功
        if not correction_result.get('success', False):
            error_msg = f"作文批改失败: {correction_result.get('error', '未知错误')}"
            logger.error(error_msg)
            
            # 更新作文状态为失败
            update_essay_status(essay_id, "failed", error=error_msg)
            
            # 通知用户任务失败
            if user_id:
                notify_user(user_id, {
                    "type": "correction_failed",
                    "essay_id": essay_id,
                    "error": error_msg
                })
                
            return {
                "status": "error",
                "message": "批改失败，请稍后再试",
                "error": correction_result.get('error', '未知错误'),
                "error_type": correction_result.get('error_type', 'UnknownError')
            }
        
        # 处理时间
        processing_time = time.time() - start_time
        
        # 保存结果到数据库
        with db.session() as session:
            essay = session.query(Essay).get(essay_id)
            if essay:
                essay.status = "completed"
                essay.processed_time = processing_time
                essay.corrected_text = correction_result.get('corrected_text', '')
                essay.scores = json.dumps(correction_result.get('score', {}))
                essay.feedback = json.dumps(correction_result.get('feedback', {}))
                essay.errors = json.dumps(correction_result.get('errors', []))
                essay.suggestions = json.dumps(correction_result.get('improvement_suggestions', []))
                essay.grade = correction_result.get('grade', '')
                session.commit()
        
        # 通知用户任务完成
        result = {
            "status": "success",
            "essay_id": essay_id,
            "title": title,
            "original_text": content,
            "corrected_text": correction_result.get('corrected_text', ''),
            "score": correction_result.get('score', {}),
            "feedback": correction_result.get('feedback', {}),
            "errors": correction_result.get('errors', []),
            "improvement_suggestions": correction_result.get('improvement_suggestions', []),
            "word_count": correction_result.get('word_count', len(content)),
            "processing_time": processing_time,
            "grade": correction_result.get('grade', ''),
            "grade_description": correction_result.get('grade_description', '')
        }
        
        if user_id:
            notify_user(user_id, {
                "type": "correction_completed",
                "essay_id": essay_id,
                "result": result
            })
        
        logger.info(f"异步批改作文完成，ID: {essay_id}，耗时: {processing_time:.2f}秒")
        return result
        
    except Exception as e:
        logger.error(f"异步批改作文异常，ID: {essay_id}: {str(e)}", exc_info=True)
        
        # 记录失败，并在一定次数内尝试重试
        try:
            # 更新作文状态为失败
            update_essay_status(essay_id, "failed", error=str(e))
            
            # 通知用户任务失败
            if user_id:
                notify_user(user_id, {
                    "type": "correction_failed",
                    "essay_id": essay_id,
                    "error": str(e)
                })
                
            # 在重试次数内尝试重试
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # 已达到最大重试次数
            logger.error(f"作文批改任务达到最大重试次数，ID: {essay_id}")
            return {
                "status": "error",
                "message": "批改任务多次失败，请联系管理员",
                "error": str(e)
            }
```

### 4.2 用户相关任务

```python
# tasks/user_tasks.py
@shared_task(name='tasks.user_tasks.send_welcome_email')
def send_welcome_email(user_id, email, username):
    """
    发送欢迎邮件
    
    Args:
        user_id: 用户ID
        email: 用户邮箱
        username: 用户名
    """
    try:
        email_service = EmailService()
        result = email_service.send_welcome_email(email, username)
        
        # 记录邮件发送结果
        logger.info(f"欢迎邮件发送结果，用户ID: {user_id}, 结果: {result}")
        return {"status": "success", "message": "欢迎邮件已发送"}
    
    except Exception as e:
        logger.error(f"发送欢迎邮件失败，用户ID: {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}

@shared_task(name='tasks.user_tasks.reset_monthly_essay_count')
def reset_monthly_essay_count():
    """
    重置用户的月度作文数量限制
    通常由Celery Beat定时调度，每月运行一次
    """
    try:
        today = datetime.now()
        logger.info(f"开始重置用户月度作文数量, 当前日期: {today.strftime('%Y-%m-%d')}")
        
        # 找出需要重置的用户
        with db.session() as session:
            profiles = session.query(UserProfile).all()
            reset_count = 0
            
            for profile in profiles:
                # 检查是否需要重置
                if profile.reset_date is None or \
                   (today - profile.reset_date).days >= 30:
                    
                    # 重置月度使用量
                    profile.essay_monthly_used = 0
                    profile.reset_date = today
                    reset_count += 1
            
            # 提交所有更改
            if reset_count > 0:
                session.commit()
                
        logger.info(f"月度作文数量重置完成，总共重置: {reset_count}个用户")
        return {
            "status": "success", 
            "reset_count": reset_count,
            "message": f"已重置{reset_count}个用户的月度作文数量限制"
        }
    
    except Exception as e:
        logger.error(f"重置月度作文数量失败: {str(e)}")
        return {"status": "error", "message": str(e)}
```

## 5. API接口设计

### 5.1 作文提交接口

```python
@correction_bp.route('/submit', methods=['POST'])
def submit_essay():
    """提交作文进行批改"""
    # 获取请求数据
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "未提供请求数据"
        }), 400
    
    # 获取作文数据
    title = data.get('title')
    content = data.get('content')
    grade = data.get('grade')
    
    # 检查是否异步处理，默认为异步
    is_async = data.get('async', True)
    
    # 验证作文数据
    validation_result = validate_essay_submission(title, content)
    if not validation_result['valid']:
        return jsonify({
            "status": "error",
            "message": validation_result['message']
        }), 400
    
    # 获取用户ID（如果已登录）
    user_id = g.user.id if hasattr(g, 'user') and g.user.is_authenticated() else None
    
    try:
        # 创建作文记录
        essay = Essay(
            user_id=user_id if user_id else 0,  # 0表示匿名用户
            title=title,
            original_text=content,
            word_count=len(content.split()),
            grade=grade,
            status='pending',
            submission_time=datetime.utcnow()
        )
        
        # 保存到数据库
        db.session.add(essay)
        db.session.commit()
        
        # 根据模式选择处理方式
        if is_async:
            # 异步模式：提交任务到队列
            task = process_essay_correction.delay(
                essay.id, title, content, user_id, grade
            )
            
            # 更新任务ID
            essay.task_id = task.id
            essay.status = 'processing'
            db.session.commit()
            
            # 返回任务信息
            return jsonify({
                "status": "success",
                "data": {
                    "essay_id": essay.id,
                    "title": title,
                    "status": "processing",
                    "task_id": task.id,
                    "message": "作文已提交批改，正在异步处理中"
                }
            }), 202  # 202 Accepted
        else:
            # 同步模式：直接处理
            # ...同步处理代码
    except Exception as e:
        # 错误处理...
```

### 5.2 任务状态查询接口

```python
@app.route('/api/tasks/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    from tasks.celery_app import celery_app
    
    task = celery_app.AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": task.status,
    }
    
    if task.status == 'SUCCESS':
        response["result"] = task.result
    elif task.status == 'FAILURE':
        response["error"] = str(task.result)
        
    return jsonify(response)
```

### 5.3 作文状态查询接口

```python
@correction_bp.route('/status/<int:essay_id>', methods=['GET'])
def get_essay_status(essay_id):
    """获取作文批改状态"""
    try:
        # 查询作文
        essay = Essay.query.get(essay_id)
        
        if not essay:
            return jsonify({
                "status": "error",
                "message": "作文不存在"
            }), 404
        
        # 检查权限（仅允许作者或管理员访问）
        user_id = g.user.id if hasattr(g, 'user') and g.user.is_authenticated() else None
        is_admin = hasattr(g, 'user') and g.user.role == 'admin'
        
        if not is_admin and essay.user_id != user_id:
            return jsonify({
                "status": "error",
                "message": "无权访问此作文"
            }), 403
        
        # 准备状态数据
        status_data = {
            "essay_id": essay.id,
            "title": essay.title,
            "status": essay.status,
            "submission_time": essay.submission_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 根据状态添加不同的数据
        if essay.status == 'failed':
            status_data["error"] = essay.error_message
            
        elif essay.status == 'completed':
            # 如果完成，添加完整结果
            status_data["result"] = essay.to_dict()
            
        # 如果有任务ID，也返回
        if essay.task_id:
            status_data["task_id"] = essay.task_id
        
        return jsonify({
            "status": "success",
            "data": status_data
        }), 200
        
    except Exception as e:
        logger.error(f"获取作文状态失败，ID: {essay_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "服务器内部错误",
            "error": str(e)
        }), 500
```

## 6. 启动脚本

### 6.1 Celery Worker启动脚本

```python
# scripts/start_workers.py
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

def start_worker(queue='default', concurrency=2, loglevel='info'):
    """
    启动Celery工作进程
    
    Args:
        queue: 队列名称，默认为default
        concurrency: 并发数，默认为2
        loglevel: 日志级别，默认为info
    """
    os.chdir(ROOT_DIR)
    cmd = [
        'celery', '-A', 'tasks.celery_app:celery_app', 'worker',
        '--loglevel', loglevel,
        '--concurrency', str(concurrency),
        '-Q', queue,
        '-n', f'worker.{queue}@%h'
    ]
    
    print(f"启动Celery工作进程: {' '.join(cmd)}")
    process = subprocess.Popen(cmd)
    return process

def start_beat():
    """启动Celery定时任务调度器"""
    os.chdir(ROOT_DIR)
    cmd = [
        'celery', '-A', 'tasks.celery_app:celery_app', 'beat',
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
    
    args = parser.parse_args()
    processes = []
    
    # 如果没有指定具体队列，则启动所有
    if not any([args.corrections, args.users, args.default, args.beat]):
        args.all = True
    
    if args.all or args.default:
        processes.append(start_worker('default', args.concurrency, args.loglevel))
    
    if args.all or args.corrections:
        processes.append(start_worker('correction', args.concurrency, args.loglevel))
    
    if args.all or args.users:
        processes.append(start_worker('users', args.concurrency, args.loglevel))
    
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
```

### 6.2 全系统启动脚本

```python
# start_all.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改系统一键启动脚本
同时启动Web应用、WebSocket和Celery工作进程
"""

import os
import sys
import subprocess
import signal
import time
import argparse
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 所有进程
processes = []

def start_web_server(host='0.0.0.0', port=5000, debug=False):
    """启动Web服务器"""
    # ...实现代码...

def start_celery_workers(concurrency=2, loglevel='info'):
    """启动Celery工作进程"""
    # ...实现代码...

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='一键启动作文批改系统')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Web服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='Web服务器端口')
    parser.add_argument('--debug', action='store_true', help='开启调试模式')
    parser.add_argument('--concurrency', type=int, default=2, help='Celery工作进程的并发数')
    parser.add_argument('--loglevel', type=str, default='info', help='日志级别')
    parser.add_argument('--web-only', action='store_true', help='仅启动Web服务器')
    parser.add_argument('--workers-only', action='store_true', help='仅启动Celery工作进程')
    
    args = parser.parse_args()
    
    # 注册信号处理器，用于优雅关闭
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=== 作文批改系统启动 ===")
    
    # ...启动服务的具体实现...

if __name__ == '__main__':
    main()
```

## 7. 实时通知集成

异步任务完成后通过WebSocket通知用户：

```python
# 在任务完成时发送通知
def notify_user(user_id, data):
    """向用户发送通知"""
    if socketio:
        socketio.emit('notification', data, room=f'user_{user_id}')
        logger.debug(f"已发送通知到用户 {user_id}: {data['type']}")
```

## 8. 任务状态更新与监控

```python
def update_essay_status(essay_id, status, error=None):
    """更新作文状态"""
    try:
        with db.session() as session:
            essay = session.query(Essay).get(essay_id)
            if essay:
                essay.status = status
                if error:
                    essay.error_message = error
                session.commit()
                
                # 发送状态更新通知
                if essay.user_id:
                    from utils.websocket_manager import send_essay_status_update
                    send_essay_status_update(essay_id, status, error=error)
                    
        logger.info(f"更新作文状态为: {status}，ID: {essay_id}")
    except Exception as e:
        logger.error(f"更新作文状态失败，ID: {essay_id}: {str(e)}")
```

## 9. 异步任务设计最佳实践

1. **任务原子性**：每个任务应该是原子的，专注于一个特定功能
2. **失败重试**：为关键任务添加重试机制，特别是网络操作
3. **状态跟踪**：记录任务状态，方便用户查询和排错
4. **结果持久化**：将任务结果保存到数据库，而非仅依赖Celery结果后端
5. **任务分区**：根据任务类型划分不同队列，避免某类任务阻塞其他任务
6. **资源限制**：设置合理的并发数和时间限制，避免资源耗尽
7. **监控与报警**：实现任务执行监控和失败报警机制 