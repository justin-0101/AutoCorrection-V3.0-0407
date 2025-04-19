#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API调用监控模块
用于记录和监控API调用的情况
"""

import os
import json
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import threading
import queue

# 配置日志
logger = logging.getLogger(__name__)

class APIMonitor:
    """API调用监控器"""
    
    def __init__(self):
        """初始化API监控器"""
        self.log_queue = queue.Queue()
        self.log_thread = None
        self.running = False
        
        # 配置日志记录器
        self.logger = logging.getLogger('api_monitor')
        self.logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        log_dir = os.path.join(os.getcwd(), 'logs', 'api')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'api_{datetime.now().strftime("%Y%m%d")}.log')
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 设置格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        
        # 启动日志处理线程
        self.start()
        
        logger.info(f"API监控器初始化完成，日志保存在：{log_file}")
    
    def start(self):
        """启动日志处理线程"""
        if not self.running:
            self.running = True
            self.log_thread = threading.Thread(target=self._process_log_queue, daemon=True)
            self.log_thread.start()
    
    def _process_log_queue(self):
        """处理异步日志队列"""
        while self.running:
            try:
                # 从队列获取日志条目
                log_entry = self.log_queue.get()
                
                # 写入日志
                self._write_log(log_entry)
                
                # 标记任务完成
                self.log_queue.task_done()
                
            except Exception as e:
                logger.error(f"处理API监控日志队列时出错: {str(e)}")
                time.sleep(1)  # 避免错误时CPU使用率过高
    
    def _write_log(self, log_entry: Dict[str, Any]):
        """
        写入日志
        
        Args:
            log_entry: 日志条目
        """
        try:
            # 写入日志
            self.logger.info(json.dumps(log_entry, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"写入API监控日志时出错: {str(e)}")
    
    def log_api_call(self, 
                    provider: str, 
                    model: str, 
                    endpoint: str, 
                    request_params: Dict[str, Any],
                    request_id: str = None,
                    **kwargs):
        """
        记录API调用开始
        
        Args:
            provider: API提供商（如deepseek, openai等）
            model: 使用的模型
            endpoint: API端点
            request_params: 请求参数
            request_id: 请求ID，如果不提供会自动生成
            **kwargs: 其他参数
        
        Returns:
            str: 请求ID
        """
        # 生成请求ID
        if not request_id:
            request_id = f"{int(time.time() * 1000)}-{threading.get_ident() % 10000}"
        
        # 创建日志条目
        log_entry = {
            "request_id": request_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "event": "api_call_start",
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "params": self._sanitize_params(request_params),
            **kwargs
        }
        
        # 添加到日志队列
        self.log_queue.put(log_entry)
        
        return request_id
    
    def log_api_response(self, 
                       request_id: str, 
                       status: str,
                       response_time: float,
                       response: Any = None,
                       error: str = None,
                       **kwargs):
        """
        记录API调用结束
        
        Args:
            request_id: 请求ID
            status: 状态（success/error）
            response_time: 响应时间（秒）
            response: 响应内容
            error: 错误信息
            **kwargs: 其他参数
        """
        # 创建日志条目
        log_entry = {
            "request_id": request_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "event": "api_call_end",
            "status": status,
            "response_time": response_time,
            **kwargs
        }
        
        # 添加响应或错误信息
        if status == "success" and response:
            log_entry["response_summary"] = self._summarize_response(response)
        
        if status == "error" and error:
            log_entry["error"] = error
        
        # 添加到日志队列
        self.log_queue.put(log_entry)
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理参数中的敏感信息
        
        Args:
            params: 原始参数
            
        Returns:
            Dict: 清理后的参数
        """
        if not params:
            return {}
            
        # 创建一个副本
        sanitized = params.copy()
        
        # 敏感字段列表
        sensitive_fields = ['api_key', 'secret', 'token', 'password']
        
        # 清理敏感字段
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "********"
        
        # 处理消息内容
        if 'messages' in sanitized and isinstance(sanitized['messages'], list):
            # 保留消息结构，但限制内容长度
            for i, msg in enumerate(sanitized['messages']):
                if 'content' in msg and isinstance(msg['content'], str) and len(msg['content']) > 100:
                    sanitized['messages'][i]['content'] = msg['content'][:100] + "..."
        
        return sanitized
    
    def _summarize_response(self, response: Any) -> Dict[str, Any]:
        """
        总结响应内容
        
        Args:
            response: 响应内容
            
        Returns:
            Dict: 总结后的内容
        """
        try:
            summary = {}
            
            # 处理不同类型的响应
            if isinstance(response, dict):
                # 获取关键字段
                if 'choices' in response:
                    summary['choices_count'] = len(response['choices'])
                    
                    # 获取第一个选择的部分内容
                    if response['choices'] and len(response['choices']) > 0:
                        first_choice = response['choices'][0]
                        if 'message' in first_choice and 'content' in first_choice['message']:
                            content = first_choice['message']['content']
                            summary['first_choice_content'] = content[:100] + "..." if len(content) > 100 else content
                
                # 获取token使用情况
                if 'usage' in response:
                    summary['usage'] = response['usage']
                
                # 获取ID和模型
                for field in ['id', 'model', 'object', 'created']:
                    if field in response:
                        summary[field] = response[field]
            
            elif isinstance(response, str):
                summary['content'] = response[:100] + "..." if len(response) > 100 else response
            
            else:
                summary['type'] = str(type(response))
            
            return summary
            
        except Exception as e:
            logger.error(f"总结响应内容时出错: {str(e)}")
            return {"error": "无法总结响应内容"}
    
    def flush(self):
        """刷新日志队列"""
        try:
            # 等待队列处理完成
            self.log_queue.join()
        except Exception as e:
            logger.error(f"刷新API监控日志队列时出错: {str(e)}")

# 创建全局监控实例
api_monitor = APIMonitor()

def log_api_call(func):
    """
    API调用装饰器
    用于自动记录API调用的情况
    
    Usage:
        @log_api_call
        def call_api(self, ...):
            ...
    """
    def wrapper(self, *args, **kwargs):
        # 获取API信息
        provider = getattr(self, 'provider_name', 'unknown')
        model = getattr(self, 'model', 'unknown')
        endpoint = func.__name__
        
        # 处理请求参数
        request_params = {}
        if args and isinstance(args[0], dict):
            request_params = args[0]
        elif kwargs:
            request_params = kwargs
        
        # 记录API调用开始
        request_id = api_monitor.log_api_call(
            provider=provider,
            model=model,
            endpoint=endpoint,
            request_params=request_params,
            function=func.__name__
        )
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 调用原始函数
            result = func(self, *args, **kwargs)
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 记录API调用成功
            api_monitor.log_api_response(
                request_id=request_id,
                status="success",
                response_time=response_time,
                response=result
            )
            
            return result
            
        except Exception as e:
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 记录API调用失败
            api_monitor.log_api_response(
                request_id=request_id,
                status="error",
                response_time=response_time,
                error=str(e),
                traceback=traceback.format_exc()
            )
            
            # 重新抛出异常
            raise
    
    return wrapper

def log_api_call_async(func):
    """
    异步API调用装饰器
    用于自动记录异步API调用的情况
    
    Usage:
        @log_api_call_async
        async def call_api_async(self, ...):
            ...
    """
    async def wrapper(self, *args, **kwargs):
        # 获取API信息
        provider = getattr(self, 'provider_name', 'unknown')
        model = getattr(self, 'model', 'unknown')
        endpoint = func.__name__
        
        # 处理请求参数
        request_params = {}
        if args and isinstance(args[0], dict):
            request_params = args[0]
        elif kwargs:
            request_params = kwargs
        
        # 记录API调用开始
        request_id = api_monitor.log_api_call(
            provider=provider,
            model=model,
            endpoint=endpoint,
            request_params=request_params,
            function=func.__name__,
            is_async=True
        )
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 调用原始异步函数
            result = await func(self, *args, **kwargs)
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 记录API调用成功
            api_monitor.log_api_response(
                request_id=request_id,
                status="success",
                response_time=response_time,
                response=result,
                is_async=True
            )
            
            return result
            
        except Exception as e:
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 记录API调用失败
            api_monitor.log_api_response(
                request_id=request_id,
                status="error",
                response_time=response_time,
                error=str(e),
                traceback=traceback.format_exc(),
                is_async=True
            )
            
            # 重新抛出异常
            raise
    
    return wrapper 