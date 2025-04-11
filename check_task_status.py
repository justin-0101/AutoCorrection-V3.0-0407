#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
任务状态查询工具
用于检查和管理系统中的任务状态记录
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import logging

# 确保系统路径正确
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.models.task_status import TaskStatus, TaskState
from app.extensions import db
from sqlalchemy import desc, func

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def format_time(dt):
    """格式化时间"""
    if not dt:
        return "未设置"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_duration(start, end):
    """计算并格式化时长"""
    if not start:
        return "未开始"
    end_time = end or datetime.utcnow()
    duration = (end_time - start).total_seconds()
    if duration < 60:
        return f"{duration:.2f}秒"
    elif duration < 3600:
        return f"{duration/60:.2f}分钟"
    else:
        return f"{duration/3600:.2f}小时"

def query_tasks(status=None, task_name=None, days=1, limit=20):
    """查询任务状态记录"""
    query = TaskStatus.query
    
    # 应用过滤条件
    if status:
        query = query.filter_by(status=status)
    
    if task_name:
        query = query.filter(TaskStatus.task_name.contains(task_name))
    
    # 时间范围过滤
    if days > 0:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(TaskStatus.created_at >= cutoff_date)
    
    # 按创建时间倒序，最新的在前面
    query = query.order_by(desc(TaskStatus.created_at))
    
    # 限制结果数量
    if limit > 0:
        query = query.limit(limit)
    
    return query.all()

def print_task_details(task):
    """打印单个任务的详细信息"""
    print("\n" + "=" * 80)
    print(f"任务ID: {task.task_id}")
    print(f"任务名称: {task.task_name}")
    print(f"状态: {task.status}")
    print(f"工作节点: {task.worker_id or '未知'}")
    print(f"关联类型: {task.related_type or '无'}")
    print(f"关联ID: {task.related_id or '无'}")
    print(f"重试次数: {task.retry_count}")
    print(f"创建时间: {format_time(task.created_at)}")
    print(f"开始时间: {format_time(task.started_at)}")
    print(f"完成时间: {format_time(task.completed_at)}")
    print(f"执行时长: {format_duration(task.started_at, task.completed_at)}")
    
    if task.args:
        print(f"参数: {task.args}")
    if task.kwargs:
        print(f"关键字参数: {task.kwargs}")
    
    if task.result:
        print("\n结果:")
        for key, value in task.result.items():
            print(f"  {key}: {value}")
    
    if task.error:
        print("\n错误信息:")
        print(task.error)
    
    print("=" * 80)

def print_task_summary(tasks):
    """打印任务列表的摘要信息"""
    if not tasks:
        print("没有找到符合条件的任务记录")
        return
    
    print("\n找到 {} 条任务记录:\n".format(len(tasks)))
    print("{:<36} {:<30} {:<10} {:<20} {:<10}".format(
        "任务ID", "任务名称", "状态", "创建时间", "重试次数"))
    print("-" * 110)
    
    for task in tasks:
        task_name = task.task_name
        if len(task_name) > 28:
            task_name = task_name[:25] + "..."
            
        print("{:<36} {:<30} {:<10} {:<20} {:<10}".format(
            task.task_id,
            task_name,
            task.status,
            format_time(task.created_at),
            task.retry_count
        ))

def print_status_statistics():
    """打印各状态的任务数量统计"""
    with db.session() as session:
        stats = session.query(
            TaskStatus.status, 
            func.count(TaskStatus.id)
        ).group_by(TaskStatus.status).all()
        
        total = sum(count for _, count in stats)
        
        print("\n任务状态统计:")
        print("-" * 30)
        for status, count in stats:
            percentage = (count / total * 100) if total > 0 else 0
            print(f"{status}: {count} ({percentage:.1f}%)")
        print("-" * 30)
        print(f"总计: {total}")

def check_task_status(task_id):
    """检查指定任务ID的状态"""
    try:
        # 导入必要的模块
        from app import create_app
        from app.models.db import db
        from app.models.essay import Essay
        from app.models.correction import Correction
        from celery.result import AsyncResult
        from app.tasks.celery_app import celery_app
        
        app = create_app()
        
        with app.app_context():
            # 检查任务在Celery中的状态
            task_result = AsyncResult(task_id, app=celery_app)
            
            logger.info(f"任务ID: {task_id}")
            logger.info(f"任务状态: {task_result.state}")
            
            if task_result.ready():
                logger.info(f"任务结果: {task_result.result}")
                logger.info(f"任务是否成功: {task_result.successful()}")
                
                if task_result.failed():
                    logger.info(f"任务失败原因: {task_result.traceback}")
            
            # 查询对应的批改记录
            correction = db.session.query(Correction).filter_by(task_id=task_id).first()
            
            if correction:
                logger.info(f"找到关联的批改记录ID: {correction.id}")
                logger.info(f"批改记录状态: {correction.status}")
                logger.info(f"批改记录创建时间: {correction.created_at}")
                logger.info(f"批改记录更新时间: {correction.updated_at}")
                
                # 查询对应的作文
                essay = db.session.query(Essay).filter_by(id=correction.essay_id).first()
                
                if essay:
                    logger.info(f"关联的作文ID: {essay.id}")
                    logger.info(f"作文标题: {essay.title}")
                    logger.info(f"作文状态: {essay.status}")
                else:
                    logger.warning(f"未找到关联的作文")
            else:
                logger.warning(f"未找到任务ID为 {task_id} 的批改记录")
            
            # 查询所有正在处理中的批改记录
            correcting_corrections = db.session.query(Correction).filter_by(status="correcting").all()
            logger.info(f"当前系统中共有 {len(correcting_corrections)} 条正在处理的批改记录")
            
            for c in correcting_corrections:
                logger.info(f"  批改ID: {c.id}, 任务ID: {c.task_id}, 作文ID: {c.essay_id}")
                
                # 检查任务状态
                if c.task_id:
                    c_task = AsyncResult(c.task_id, app=celery_app)
                    logger.info(f"  任务状态: {c_task.state}")
                    
                    if c_task.ready():
                        logger.info(f"  任务已完成但批改记录未更新!")
                        
                        if c_task.failed():
                            logger.info(f"  任务失败原因: {c_task.traceback}")
                
            return True
    except Exception as e:
        logger.error(f"检查任务状态时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="任务状态查询工具")
    parser.add_argument("--status", "-s", help="按状态过滤 (pending, running, success, failed, retry)")
    parser.add_argument("--name", "-n", help="按任务名称过滤")
    parser.add_argument("--days", "-d", type=int, default=1, help="查询最近几天的记录 (默认: 1，0表示所有记录)")
    parser.add_argument("--limit", "-l", type=int, default=20, help="最多显示几条记录 (默认: 20，0表示所有记录)")
    parser.add_argument("--task-id", "-t", help="查询特定任务ID的详细信息")
    parser.add_argument("--stats", action="store_true", help="显示任务状态统计信息")
    
    args = parser.parse_args()
    
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        # 显示统计信息
        if args.stats:
            print_status_statistics()
            
        # 查询特定任务
        if args.task_id:
            task = TaskStatus.query.filter_by(task_id=args.task_id).first()
            if task:
                print_task_details(task)
            else:
                print(f"找不到任务ID为 {args.task_id} 的记录")
            return
            
        # 查询符合条件的任务列表
        tasks = query_tasks(
            status=args.status,
            task_name=args.name,
            days=args.days,
            limit=args.limit
        )
        
        print_task_summary(tasks)
        
        # 是否显示详细信息
        if tasks and len(tasks) <= 5:  # 如果结果少于5个，自动显示详情
            for task in tasks:
                print_task_details(task)
        elif tasks:
            show_details = input("\n是否显示详细信息? (y/n): ").lower().strip() == 'y'
            if show_details:
                for task in tasks:
                    print_task_details(task)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        logger.info(f"检查任务ID: {task_id}")
        check_task_status(task_id)
    else:
        logger.error("请提供任务ID")
        sys.exit(1) 