#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文章批改任务模块
包含异步处理文章批改的任务函数
"""

import os
import time
import logging
import traceback
from flask import current_app
from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import redis
from redis.exceptions import LockError

from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.core.correction.correction_service import CorrectionService
from app.extensions import db

logger = logging.getLogger(__name__)

@shared_task(bind=True, name='app.tasks.correction_tasks.process_essay_correction', queue='correction')
def process_essay_correction(self, essay_id):
    """
    处理文章批改任务
    
    Args:
        self: Celery任务实例
        essay_id: 文章ID
        
    Returns:
        dict: 包含批改结果的字典
    """
    # 导入一些必要的库，在函数内部导入避免循环导入
    import pytz
    from flask import has_app_context, current_app
    from app import create_app
    import traceback

    task_id = self.request.id
    logger.info(f"开始处理文章批改任务，文章ID: {essay_id}, 任务ID: {task_id}")
    
    # 检查是否已在应用上下文中
    app = None
    ctx = None
    redis_client = None
    lock = None
    have_lock = False
    
    try:
        # 应用上下文处理
        if not has_app_context():
            logger.info("未检测到应用上下文，正在创建新的应用上下文...")
            app = create_app()
            ctx = app.app_context()
            ctx.push()
            logger.info("已创建并推送新的应用上下文")
        else:
            logger.info("检测到现有应用上下文，继续使用当前上下文")
            app = current_app
        
        # 设置时区为Asia/Shanghai
        os.environ['TZ'] = 'Asia/Shanghai'
        try:
            # 视环境而定，Windows可能不支持tzset
            time.tzset()
            logger.info("已设置时区为Asia/Shanghai")
        except AttributeError:
            # Windows不支持tzset
            logger.warning("Windows系统不支持time.tzset()，时区设置可能不生效")
        
        # 初始化Redis客户端并尝试获取分布式锁
        try:
            redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
            redis_client = redis.Redis.from_url(redis_url)
            lock_name = f"essay_correction_lock:{essay_id}"
            lock_timeout = 600  # 10分钟锁超时
            
            # 创建锁对象
            lock = redis_client.lock(lock_name, timeout=lock_timeout)
            
            # 非阻塞方式获取锁
            have_lock = lock.acquire(blocking=False)
            
            if not have_lock:
                logger.warning(f"无法获取作文处理锁，可能已有进程正在处理: {essay_id}")
                return {"success": False, "error": "作文正在被其他进程处理"}
            
            logger.info(f"成功获取作文处理锁: {essay_id}")
        except Exception as redis_err:
            logger.error(f"Redis锁操作失败: {str(redis_err)}")
            # 继续执行，但没有分布式锁保护
        
        # 使用应用中已注册的db实例，而不是创建新的实例
        logger.info("测试数据库连接...")
        try:
            db.session.execute(text('SELECT 1'))
            logger.info("数据库连接测试成功")
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            raise
        
        # 确保没有活跃事务
        # 注释掉使用不存在方法的代码
        # if db.session.in_transaction():
        #     logger.warning("检测到活跃事务，正在回滚...")
        #     db.session.rollback()
        
        # 改为检查是否有活跃事务并尝试回滚
        try:
            if db.session.is_active:
                logger.warning("检测到活跃会话，尝试回滚任何未完成的事务...")
                db.session.rollback()
        except Exception as e:
            logger.error(f"检查或回滚事务时出错: {str(e)}")
            # 继续执行，但记录错误
        
        # 查询文章并更新状态
        logger.info(f"查询文章 ID: {essay_id}")
        
        # 使用get方法获取作文，性能更好
        essay = db.session.get(Essay, essay_id)
        
        if not essay:
            logger.error(f"找不到文章 ID: {essay_id}")
            return {"success": False, "error": f"找不到文章 ID: {essay_id}"}
        
        # 初始化批改服务
        logger.info("初始化批改服务...")
        service = CorrectionService()
        
        # 使用新的状态转换方法将作文状态改为处理中
        transition_result = service.transition_essay_state(
            essay_id, 
            EssayStatus.PENDING.value, 
            EssayStatus.CORRECTING.value
        )
        
        if not transition_result:
            logger.error(f"无法将作文状态转换为处理中: {essay_id}")
            return {"success": False, "error": "无法更新作文状态为处理中"}
            
        # 设置任务超时监控
        max_execution_time = 900  # 15分钟
        self.request.time_limit = max_execution_time
        self.request.soft_time_limit = max_execution_time - 60  # 提前1分钟触发软超时
        
        # 执行批改
        logger.info(f"开始执行文章批改: {essay_id}")
        
        # 记录批改开始时间
        start_time = time.time()
        
        # 执行批改，包含重试机制
        retry_count = 0
        max_retries = 2
        last_error = None
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    logger.info(f"第 {retry_count} 次重试批改作文: {essay_id}")
                    # 等待一段时间再重试
                    time.sleep(retry_count * 5)  # 5秒, 10秒
                
                # 执行批改
                result = service.perform_correction(essay)
                
                # 记录批改耗时
                processing_time = time.time() - start_time
                logger.info(f"文章批改完成，耗时: {processing_time:.2f} 秒")
        
                # 检查批改结果
                if isinstance(result, dict) and 'status' in result:
                    if result['status'] == 'success':
                        logger.info(f"文章批改成功: {essay_id}, 得分: {result.get('score', 'N/A')}")
                        # 批改成功，不需要额外更新状态
                        return {
                            "success": True, 
                            "result": result
                        }
                    else:
                        # 批改失败但有明确错误信息
                        error_msg = result.get('message', '未知错误')
                        last_error = error_msg
                        
                        # 如果尚未达到最大重试次数，尝试重试
                        if retry_count < max_retries:
                            retry_count += 1
                            logger.warning(f"批改失败，将重试 ({retry_count}/{max_retries}): {error_msg}")
                            continue
                        
                        # 达到最大重试次数，标记为失败
                        logger.error(f"文章批改失败(达到最大重试次数): {essay_id}, 错误: {error_msg}")
                        
                        # 使用新的状态转换方法将作文状态改为失败
                        service.transition_essay_state(
                            essay_id, 
                            EssayStatus.CORRECTING.value, 
                            EssayStatus.FAILED.value, 
                            error_msg
                        )
                
                        return {
                            "success": False, 
                            "error": error_msg
                        }
                
                # 返回值格式不符合预期
                logger.error(f"批改返回格式不符合预期: {result}")
                last_error = "批改返回格式不符合预期"
                retry_count += 1
                
            except Exception as e:
                # 处理异常
                error_msg = f"批改过程异常: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                last_error = error_msg
                retry_count += 1
                
                # 如果尚未达到最大重试次数，尝试重试
                if retry_count <= max_retries:
                    logger.warning(f"批改异常，将重试 ({retry_count}/{max_retries})")
                    continue
        
        # 所有重试都失败，最终标记为失败
        logger.error(f"所有批改尝试都失败: {essay_id}, 最后错误: {last_error}")
        
        # 使用新的状态转换方法将作文状态改为失败
        service.transition_essay_state(
            essay_id, 
            EssayStatus.CORRECTING.value, 
            EssayStatus.FAILED.value, 
            last_error
        )
            
        return {"success": False, "error": last_error}
        
    except Exception as e:
        error_msg = f"处理文章批改任务出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # 尝试标记文章为错误状态
        try:
            # 初始化批改服务并转换状态
            service = CorrectionService()
            service.transition_essay_state(
                essay_id, 
                EssayStatus.CORRECTING.value, 
                EssayStatus.FAILED.value, 
                error_msg
            )
        except Exception as ex:
            logger.error(f"无法更新文章错误状态: {str(ex)}")
            
        return {"success": False, "error": error_msg}
        
    finally:
        # 清理资源
        try:
            # 释放分布式锁
            if have_lock and lock:
                try:
                    lock.release()
                    logger.info(f"已释放作文处理锁: {essay_id}")
                except LockError as lock_err:
                    logger.error(f"释放锁失败: {str(lock_err)}")
                    
            # 关闭Redis连接
            if redis_client:
                redis_client.close()
        
            # 关闭应用上下文
            if ctx:
                ctx.pop()
                logger.info("已弹出应用上下文")
        except Exception as cleanup_err:
            logger.error(f"清理资源失败: {str(cleanup_err)}")