#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批处理任务优化模块
提供批量数据处理和性能优化的工具函数
"""

import logging
import time
import math
import concurrent.futures
from functools import wraps
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional, Tuple, Union, Iterator
import threading

from sqlalchemy.orm import Session
from app.models.db import db
from app.tasks.logging_config import get_task_logger

# 获取任务专用日志记录器
logger = get_task_logger()

# 线程局部存储，用于保存每个线程的上下文数据
thread_local = threading.local()

def batch_processor(
    items: List[Any], 
    process_func: Callable[[Any], Any], 
    batch_size: int = 100,
    max_workers: int = 4,
    use_threading: bool = True,
    error_handler: Optional[Callable[[Any, Exception], None]] = None
) -> Dict[str, Any]:
    """
    通用批处理函数，支持多线程处理
    
    Args:
        items: 待处理的项目列表
        process_func: 处理单个项目的函数，接受一个项目作为参数，返回处理结果
        batch_size: 每批处理的项目数量
        max_workers: 最大工作线程数
        use_threading: 是否使用多线程处理
        error_handler: 错误处理函数，接受项目和异常作为参数
        
    Returns:
        Dict: 处理结果
    """
    start_time = time.time()
    total_items = len(items)
    processed_count = 0
    error_count = 0
    results = []
    errors = []
    
    logger.info(f"开始批处理 {total_items} 项，批次大小: {batch_size}, 最大工作线程: {max_workers}")

    # 将项目分成批次
    batches = [items[i:i + batch_size] for i in range(0, total_items, batch_size)]
    
    # 定义批处理函数
    def process_batch(batch):
        batch_results = []
        batch_errors = []
        batch_processed = 0
        batch_failed = 0
        
        for item in batch:
            try:
                result = process_func(item)
                batch_results.append(result)
                batch_processed += 1
            except Exception as e:
                batch_failed += 1
                error_info = {"item": item, "error": str(e)}
                batch_errors.append(error_info)
                if error_handler:
                    try:
                        error_handler(item, e)
                    except Exception as handler_error:
                        logger.error(f"错误处理器异常: {str(handler_error)}")
        
        return {
            "processed": batch_processed,
            "failed": batch_failed,
            "results": batch_results,
            "errors": batch_errors
        }
    
    # 使用多线程或直接处理
    if use_threading and max_workers > 1 and len(batches) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_batch, batch) for batch in batches]
            
            # 收集结果
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_result = future.result()
                    processed_count += batch_result["processed"]
                    error_count += batch_result["failed"]
                    results.extend(batch_result["results"])
                    errors.extend(batch_result["errors"])
                except Exception as e:
                    logger.error(f"批处理任务异常: {str(e)}")
                    error_count += 1
    else:
        # 单线程处理
        for batch in batches:
            batch_result = process_batch(batch)
            processed_count += batch_result["processed"]
            error_count += batch_result["failed"]
            results.extend(batch_result["results"])
            errors.extend(batch_result["errors"])
    
    processing_time = time.time() - start_time
    
    logger.info(f"批处理完成，成功: {processed_count}, 失败: {error_count}, 耗时: {processing_time:.2f}秒")
    
    return {
        "status": "success" if error_count == 0 else "partial_success" if processed_count > 0 else "error",
        "total": total_items,
        "processed": processed_count,
        "failed": error_count,
        "processing_time": processing_time,
        "results": results,
        "errors": errors
    }


def iterate_in_chunks(query, chunk_size=1000):
    """
    优化的大数据集查询迭代器，避免一次性加载所有数据到内存中
    
    Args:
        query: SQLAlchemy查询对象
        chunk_size: 每次获取的记录数量
        
    Yields:
        每批查询结果
    """
    offset = 0
    while True:
        chunk = query.limit(chunk_size).offset(offset).all()
        if not chunk:
            break
        yield chunk
        offset += chunk_size


def chunked_insert(
    session: Session, 
    model_class: Any, 
    data: List[Dict], 
    chunk_size: int = 1000
) -> Dict[str, Any]:
    """
    优化的批量插入函数，将数据分块插入以避免单个事务过大
    
    Args:
        session: 数据库会话
        model_class: 模型类
        data: 待插入的数据列表，每项是字典格式
        chunk_size: 每批插入的记录数量
        
    Returns:
        Dict: 处理结果
    """
    start_time = time.time()
    total_records = len(data)
    inserted_count = 0
    error_count = 0
    chunk_count = math.ceil(total_records / chunk_size)
    
    logger.info(f"开始分块插入 {total_records} 条记录，每批 {chunk_size} 条，预计 {chunk_count} 个批次")
    
    for i in range(0, total_records, chunk_size):
        chunk = data[i:i+chunk_size]
        try:
            # 创建模型实例列表
            instances = [model_class(**item) for item in chunk]
            
            # 批量插入
            session.bulk_save_objects(instances)
            session.commit()
            
            inserted_count += len(chunk)
            logger.debug(f"已插入批次 {i//chunk_size + 1}/{chunk_count}，进度: {inserted_count}/{total_records}")
        
        except Exception as e:
            session.rollback()
            error_count += len(chunk)
            logger.error(f"批次 {i//chunk_size + 1}/{chunk_count} 插入失败: {str(e)}")
    
    processing_time = time.time() - start_time
    logger.info(f"分块插入完成，成功: {inserted_count}，失败: {error_count}，耗时: {processing_time:.2f}秒")
    
    return {
        "status": "success" if error_count == 0 else "partial_success" if inserted_count > 0 else "error",
        "total": total_records,
        "inserted": inserted_count,
        "failed": error_count,
        "processing_time": processing_time
    }


def get_thread_session():
    """
    获取当前线程的数据库会话
    确保多线程环境中每个线程使用独立的会话
    
    Returns:
        SQLAlchemy会话
    """
    if not hasattr(thread_local, "session"):
        thread_local.session = db.create_scoped_session()
    return thread_local.session


def with_thread_session(func):
    """
    装饰器，为被装饰的函数提供线程安全的数据库会话
    
    Args:
        func: 需要装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = get_thread_session()
        try:
            return func(session=session, *args, **kwargs)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    return wrapper


def monitor_performance(name=None):
    """
    性能监控装饰器，记录函数执行时间和资源使用情况
    
    Args:
        name: 监控名称，默认为函数名
        
    Returns:
        装饰后的函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = name or func.__name__
            start_time = time.time()
            
            try:
                # 记录开始信息
                logger.debug(f"[性能] {func_name} 开始执行")
                
                # 调用原函数
                result = func(*args, **kwargs)
                
                # 计算执行时间
                execution_time = time.time() - start_time
                
                # 记录性能信息
                logger.info(f"[性能] {func_name} 执行完成, 耗时: {execution_time:.3f}秒")
                
                # 如果返回的是字典，添加执行时间信息
                if isinstance(result, dict):
                    result["execution_time"] = execution_time
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"[性能] {func_name} 执行异常, 耗时: {execution_time:.3f}秒, 错误: {str(e)}")
                raise
        
        return wrapper
    
    return decorator


def prioritize_task(priority_func):
    """
    任务优先级装饰器，根据函数返回的优先级值调整任务优先级
    
    Args:
        priority_func: 计算优先级的函数，接收与原任务相同的参数，返回优先级值(1-10)
        
    Returns:
        装饰后的任务函数
    """
    def decorator(task_func):
        @wraps(task_func)
        def wrapper(self, *args, **kwargs):
            # 计算优先级
            try:
                priority = priority_func(*args, **kwargs)
                # 确保优先级在有效范围内
                priority = max(1, min(10, priority))
            except Exception as e:
                logger.warning(f"计算任务优先级失败，使用默认优先级: {str(e)}")
                priority = 5  # 默认中等优先级
            
            # 设置任务优先级
            setattr(self.request, 'priority', priority)
            logger.info(f"任务 {self.request.id} 设置优先级: {priority}")
            
            # 执行原任务
            return task_func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator 