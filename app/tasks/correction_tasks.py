#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改异步任务模块 - 依赖注入版本
提供作文批改相关的异步任务处理，使用依赖注入解决循环导入问题
"""

import logging
import traceback
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import time

from celery import shared_task
from dependency_injector.wiring import inject, Provide
from app.core.services.service_registry_di import ServiceContainer
from app.core.correction.interface import ICorrectionService, CorrectionResult
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.utils.exceptions import ResourceNotFoundError, ProcessingError

# 获取任务专用日志记录器
logger = logging.getLogger('app.tasks.correction')

def validate_essay_id(essay_id):
    """
    验证作文ID
    
    Args:
        essay_id: 作文ID
        
    Returns:
        tuple: (bool, str) - (是否有效, 错误消息)
    """
    # 检查是否为None或空
    if essay_id is None:
        return False, "作文ID不能为空"
        
    # 检查类型
    if not isinstance(essay_id, int) and not (isinstance(essay_id, str) and essay_id.isdigit()):
        return False, f"作文ID必须是整数，当前类型: {type(essay_id)}"
        
    # 转换为整数并检查范围
    try:
        essay_id = int(essay_id)
        if essay_id <= 0:
            return False, f"作文ID必须是正整数，当前值: {essay_id}"
    except (ValueError, TypeError):
        return False, f"无法将作文ID转换为整数: {essay_id}"
        
    return True, ""

@shared_task(bind=True, max_retries=5)
@inject
def process_essay_correction(
    self, 
    essay_id: int,
    correction_service: ICorrectionService = Provide[ServiceContainer.correction_service]
):
    """
    异步处理作文批改任务
    
    Args:
        self: Celery任务实例
        essay_id: 作文ID
        correction_service: 批改服务（通过依赖注入提供）
    
    Returns:
        Dict: 批改结果
    """
    task_id = self.request.id
    
    # 记录任务开始信息
    logger.info(f"[{task_id}] 开始异步处理作文批改，作文ID: {essay_id}")
    
    # 参数验证
    is_valid, error_message = validate_essay_id(essay_id)
    if not is_valid:
        logger.error(f"[{task_id}] 作文ID无效: {error_message}")
        return {
            'status': 'error',
            'message': error_message,
            'task_id': task_id
        }
    
    # 转换为整数
    essay_id = int(essay_id)
    
    try:
        # 查询数据库
        from app.extensions import db
        
        # 重试机制，查找作文
        retry_attempts = 3
        essay = None
        
        for attempt in range(retry_attempts):
            essay = Essay.query.get(essay_id)
            
            if essay:
                break
                
            logger.warning(f"[{task_id}] 尝试 {attempt+1}/{retry_attempts} - 找不到作文 ID: {essay_id}，等待后重试...")
            time.sleep(1 * (attempt + 1))  # 递增等待时间
        
        if not essay:
            error_msg = f"经过 {retry_attempts} 次尝试后作文仍不存在，ID: {essay_id}"
            logger.error(f"[{task_id}] {error_msg}")
            
            # 尝试检查数据库连接
            try:
                test_query = db.session.execute("SELECT 1")
                logger.info(f"[{task_id}] 数据库连接测试: {list(test_query)}")
            except Exception as db_test_error:
                logger.error(f"[{task_id}] 数据库连接测试失败: {str(db_test_error)}")
            
            # 尝试重新获取，使用不同的查询方式
            try:
                alt_essay = db.session.query(Essay).filter(Essay.id == essay_id).first()
                if alt_essay:
                    logger.info(f"[{task_id}] 使用替代查询方法找到作文: {alt_essay.id}")
                    essay = alt_essay
                else:
                    logger.error(f"[{task_id}] 替代查询方法也找不到作文 ID: {essay_id}")
            except Exception as alt_query_error:
                logger.error(f"[{task_id}] 替代查询失败: {str(alt_query_error)}")
            
            # 如果仍然找不到，返回错误
            if not essay:
                return {
                    'status': 'error',
                    'message': error_msg,
                    'task_id': task_id
                }
            
        # 如果已完成，跳过处理
        if essay.status == EssayStatus.COMPLETED.value:
            logger.info(f"[{task_id}] 作文已完成批改，跳过处理，ID: {essay_id}")
            return {
                'status': 'skipped',
                'message': '作文已完成批改',
                'task_id': task_id
            }
            
        # 更新状态为处理中
        old_status = essay.status
        essay.status = EssayStatus.PROCESSING.value
        
        # 查找或创建批改记录
        correction = Correction.query.filter_by(essay_id=essay_id).first()
        if not correction:
            correction = Correction(
                essay_id=essay_id,
                status=CorrectionStatus.PROCESSING.value,
                task_id=task_id
            )
            db.session.add(correction)
        else:
            correction.status = CorrectionStatus.PROCESSING.value
            correction.task_id = task_id
        
        # 提交状态变更
        try:
            db.session.commit()
            logger.info(f"[{task_id}] 更新状态: {old_status} -> {essay.status}")
        except Exception as db_error:
            db.session.rollback()
            logger.error(f"[{task_id}] 更新状态失败: {str(db_error)}")
            raise
            
        # 执行批改
        try:
            # 使用注入的批改服务
            logger.info(f"[{task_id}] 开始执行批改，作文ID: {essay_id}")
            result = correction_service.perform_correction(essay_id)
            logger.info(f"[{task_id}] 批改执行完成，作文ID: {essay_id}, 状态: {result.get('status')}")
            
            return result
            
        except Exception as correction_error:
            # 处理批改过程中的错误
            error_message = str(correction_error)
            logger.error(f"[{task_id}] 批改过程出错: {error_message}")
            
            # 更新状态为失败
            essay.status = EssayStatus.FAILED.value
            correction.status = CorrectionStatus.FAILED.value
            correction.error_message = error_message
            
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                
            # 重试逻辑
            retry_count = self.request.retries
            if retry_count < 3:  # 最多重试3次
                logger.info(f"[{task_id}] 将在 {30 * (2 ** retry_count)} 秒后重试 ({retry_count+1}/3)")
                self.retry(exc=correction_error, countdown=30 * (2 ** retry_count))
                
            return {
                'status': 'error',
                'message': f"批改失败: {error_message}",
                'task_id': task_id
            }
            
    except Exception as e:
        # 处理未捕获的异常
        error_tb = traceback.format_exc()
        logger.error(f"[{task_id}] 处理作文批改任务异常，作文ID: {essay_id}, 错误: {str(e)}")
        logger.error(f"[{task_id}] 错误堆栈: {error_tb}")
        
        # 重试判断
        if self.request.retries < self.max_retries:
            logger.info(f"[{task_id}] 将在60秒后第{self.request.retries+1}次重试")
            self.retry(exc=e, countdown=60)
            
        return {
            'status': 'error',
            'message': f"批改过程发生未处理的异常: {str(e)}",
            'task_id': task_id
        }

@shared_task(bind=True)
@inject
def high_priority_essay_correction(
    self, 
    essay_id: int,
    correction_service: ICorrectionService = Provide[ServiceContainer.correction_service]
):
    """
    高优先级的作文批改任务
    
    Args:
        self: Celery任务实例
        essay_id: 作文ID
        correction_service: 批改服务（通过依赖注入提供）
    
    Returns:
        Dict: 处理结果
    """
    logger.info(f"开始高优先级作文批改 [essay_id={essay_id}]")
    
    is_valid, error_message = validate_essay_id(essay_id)
    if not is_valid:
        return {"status": "error", "message": error_message}
    
    # 转换为整数
    essay_id = int(essay_id)
    
    # 直接执行批改
    result = process_essay_correction.apply_async(
        args=[essay_id],
        queue='high_priority'
    )
    
    # 返回任务ID
    return {
        "status": "submitted",
        "task_id": result.id,
        "essay_id": essay_id,
        "message": "高优先级批改任务已提交"
    }

@shared_task(bind=True)
@inject
def batch_process_essays(
    self, 
    essay_ids: List[int],
    priority: bool = False,
    correction_service: ICorrectionService = Provide[ServiceContainer.correction_service]
) -> Dict[str, Any]:
    """
    批量处理作文批改任务
    
    Args:
        self: Celery任务实例
        essay_ids: 作文ID列表
        priority: 是否高优先级
        correction_service: 批改服务（通过依赖注入提供）
    
    Returns:
        Dict: 批处理结果
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] 开始批量处理作文批改，数量: {len(essay_ids)}, 优先级: {'高' if priority else '普通'}")
    
    if not essay_ids:
        return {"status": "error", "message": "作文ID列表为空"}
    
    # 检查每个ID的有效性
    valid_ids = []
    invalid_ids = []
    
    for essay_id in essay_ids:
        is_valid, _ = validate_essay_id(essay_id)
        if is_valid:
            valid_ids.append(int(essay_id))
        else:
            invalid_ids.append(essay_id)
    
    # 记录无效ID
    if invalid_ids:
        logger.warning(f"[{task_id}] 批量处理中存在无效的作文ID: {invalid_ids}")
    
    # 提交有效ID的处理任务
    results = {
        "status": "submitted",
        "task_id": task_id,
        "total": len(essay_ids),
        "valid": len(valid_ids),
        "invalid": len(invalid_ids),
        "submitted_tasks": []
    }
    
    queue = 'high_priority' if priority else 'correction'
    
    for essay_id in valid_ids:
        # 提交单个处理任务
        task = process_essay_correction.apply_async(
            args=[essay_id],
            queue=queue
        )
        
        results["submitted_tasks"].append({
            "essay_id": essay_id,
            "task_id": task.id
        })
    
    logger.info(f"[{task_id}] 批量处理任务已提交，有效ID: {len(valid_ids)}, 无效ID: {len(invalid_ids)}")
    return results 