#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务调度器模块
用于定期执行维护任务
"""

# 在导入任何其他模块之前应用eventlet猴子补丁
import os
import sys

try:
    import eventlet
    eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)
    os.environ['EVENTLET_PATCHED'] = 'true'
    print("eventlet猴子补丁已在scheduler模块中应用")
except ImportError:
    print("警告: 未安装eventlet，某些功能可能无法正常工作")

import datetime
import logging
import time
import threading
import schedule
from app.config import get_settings
from app.tasks.maintenance_tasks import fix_empty_correction_results, verify_database_integrity
from celery.schedules import crontab

# 配置日志
logger = logging.getLogger(__name__)

class TaskScheduler:
    """
    任务调度器，用于定期执行维护任务
    """
    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self.scheduler_thread = None
        self.jobs = []
        
    def setup_jobs(self):
        """设置定时任务"""
        logger.info("设置定时任务...")
        
        # 清除所有现有的任务
        schedule.clear()
        
        # 添加维护任务 - 每日凌晨3点执行修复空批改结果任务
        schedule.every().day.at("03:00").do(self._run_task, 
                                           task_func=fix_empty_correction_results,
                                           task_name="修复空批改结果")
        
        # 每周日凌晨4点执行数据库完整性验证
        schedule.every().sunday.at("04:00").do(self._run_task,
                                             task_func=verify_database_integrity,
                                             task_name="数据库完整性验证")
        
        # 可以添加更多定时任务...
        
        logger.info("定时任务设置完成")
    
    def _run_task(self, task_func, task_name):
        """
        执行任务并记录日志
        
        Args:
            task_func: 要执行的任务函数
            task_name: 任务名称（用于日志）
        
        Returns:
            任务执行结果
        """
        try:
            logger.info(f"开始执行定时任务: {task_name}")
            start_time = time.time()
            
            # 执行任务
            result = task_func()
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            logger.info(f"任务 {task_name} 执行完成，耗时: {execution_time:.2f}秒")
            logger.info(f"任务 {task_name} 执行结果: {result}")
            
            return result
        except Exception as e:
            logger.error(f"任务 {task_name} 执行失败: {str(e)}")
            logger.exception(e)
            return {"error": str(e)}
    
    def run_scheduler(self):
        """运行调度器主循环"""
        logger.info("启动任务调度器...")
        self.running = True
        
        while self.running:
            try:
                # 运行所有待执行的任务
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器循环出错: {str(e)}")
                logger.exception(e)
                time.sleep(300)  # 出错后等待5分钟再继续
    
    def start(self):
        """启动调度器线程"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("调度器已在运行中")
            return
            
        # 设置定时任务
        self.setup_jobs()
        
        # 创建并启动调度器线程
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("任务调度器已启动")
        
    def stop(self):
        """停止调度器线程"""
        logger.info("正在停止任务调度器...")
        self.running = False
        
        if self.scheduler_thread:
            # 等待线程结束
            if self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
            
            self.scheduler_thread = None
            
        logger.info("任务调度器已停止")
    
    def run_task_now(self, task_func, task_name):
        """
        立即执行指定任务
        
        Args:
            task_func: 要执行的任务函数
            task_name: 任务名称
            
        Returns:
            任务执行结果
        """
        logger.info(f"手动触发任务执行: {task_name}")
        return self._run_task(task_func, task_name)


# 创建全局调度器实例
scheduler = TaskScheduler()

def run_schedule():
    """
    运行调度器循环，定期执行计划任务
    """
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次待执行的任务
        except Exception as e:
            logger.error(f"调度器运行错误: {str(e)}")
            time.sleep(300)  # 出错后等待5分钟再重试

def database_integrity_check_job():
    """
    数据库完整性检查任务
    
    执行数据库完整性验证，并记录结果
    """
    logger.info("开始执行定时数据库完整性检查...")
    
    try:
        results = verify_database_integrity()
        
        if results.get('error'):
            logger.error(f"数据库完整性检查出错: {results.get('error')}")
        else:
            issues_found = results.get('issues_found', 0)
            issues_fixed = results.get('issues_fixed', 0)
            
            if issues_found > 0:
                logger.info(f"数据库完整性检查完成: 发现 {issues_found} 个问题，修复了 {issues_fixed} 个问题")
                
                # 记录详细问题统计
                details = results.get('details', {})
                for key, value in details.items():
                    logger.info(f"  - {key}: {value}")
            else:
                logger.info("数据库完整性检查完成: 未发现问题")
                
    except Exception as e:
        logger.error(f"执行数据库完整性检查任务时出错: {str(e)}")

def start_scheduler():
    """
    启动任务调度器
    
    设置并启动定时任务:
    1. 数据库完整性检查 - 每天凌晨3点运行
    """
    logger.info("正在启动任务调度器...")
    
    # 设置数据库完整性检查任务 - 每天凌晨3点运行
    schedule.every().day.at("03:00").do(database_integrity_check_job)
    
    # 在启动时也运行一次数据库完整性检查
    logger.info("执行初始数据库完整性检查...")
    database_integrity_check_job()
    
    # 创建并启动调度器线程
    scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
    scheduler_thread.start()
    
    logger.info("任务调度器已启动，设置了以下定时任务:")
    logger.info("  - 数据库完整性检查: 每天凌晨3点")
    
    return scheduler_thread

def stop_scheduler():
    """停止任务调度器"""
    scheduler.stop()

def run_maintenance_now():
    """立即运行所有维护任务"""
    logger.info("手动触发所有维护任务")
    
    results = {
        "empty_results_fix": scheduler.run_task_now(
            fix_empty_correction_results, "修复空批改结果"),
        "db_integrity": scheduler.run_task_now(
            verify_database_integrity, "数据库完整性验证")
    }
    
    return results

def setup_periodic_tasks(sender, **kwargs):
    """设置定时任务"""
    # 导入任务
    from app.tasks.maintenance_tasks import (
        cleanup_stale_task_statuses, 
        archive_old_task_statuses,
        verify_database_integrity,
        reset_stuck_essays
    )
    
    # 初始数据库完整性检查
    logger.info("执行初始数据库完整性检查...")
    try:
        logger.info("开始执行定时数据库完整性检查...")
        result = verify_database_integrity()
        logger.info(f"数据库完整性检查结果: {result}")
    except Exception as e:
        logger.error(f"执行数据库完整性检查任务时出错: {str(e)}")
    
    # 设置定时执行的任务
    # 每天凌晨3点执行数据库完整性检查
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        verify_database_integrity.s(),
        name='daily_db_check'
    )
    
    # 每10分钟检查一次卡住的作文并进行重置
    sender.add_periodic_task(
        600.0,  # 60秒 x 10 = 600秒 = 10分钟
        reset_stuck_essays.s(),
        name='reset_stuck_essays'
    )
    
    # 在日志中记录已设置的定时任务
    logger.info("任务调度器已启动，设置了以下定时任务:")
    logger.info("  - 数据库完整性检查: 每天凌晨3点")
    logger.info("  - 重置卡住的作文: 每10分钟") 