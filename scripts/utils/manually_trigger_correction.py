#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
import argparse
from datetime import datetime
import traceback

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.tasks.correction_tasks import process_essay_correction
from app.core.ai.deepseek_client import DeepseekClient
from app.core.correction.correction_service import CorrectionService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """手动触发作文批改任务"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='手动触发作文批改')
    parser.add_argument('essay_id', type=int, help='作文ID')
    parser.add_argument('--force', action='store_true', help='强制批改，无论当前状态')
    args = parser.parse_args()
    
    essay_id = args.essay_id
    force = args.force
    
    app = create_app()
    app.app_context().push()  # 确保在应用上下文中运行
    
    try:
        # 查找作文
        essay = db.session.query(Essay).filter(Essay.id == essay_id).first()
        if not essay:
            logger.error(f"未找到ID为{essay_id}的作文")
            return False
            
        logger.info(f"找到作文: ID={essay_id}, 标题='{essay.title}', 状态={essay.status}")
        
        if essay.status != EssayStatus.PENDING and not force:
            logger.warning(f"作文当前状态为 {essay.status}，非PENDING状态。使用--force参数强制批改。")
            return False
            
        # 获取或创建批改记录
        correction = db.session.query(Correction).filter(Correction.essay_id == essay_id).first()
        if not correction:
            logger.info(f"为作文 {essay_id} 创建新的批改记录")
            correction = Correction(
                essay_id=essay_id,
                status=CorrectionStatus.CORRECTING,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                started_at=datetime.now()
            )
            db.session.add(correction)
            db.session.commit()
            
        # 更新作文状态为批改中
        if essay.status != EssayStatus.CORRECTING or force:
            old_status = essay.status
            essay.status = EssayStatus.CORRECTING
            essay.updated_at = datetime.now()
            db.session.commit()
            logger.info(f"作文状态从 {old_status} 更新为 {essay.status}")
            
        # 创建AI客户端
        ai_client = DeepseekClient()
        
        # 直接调用批改任务
        logger.info(f"手动触发作文{essay_id}的批改任务")
        try:
            # 方法1：使用Celery任务异步处理
            # result = process_essay_correction.delay(essay_id)
            # logger.info(f"任务已提交，任务ID: {result.task_id}")
            
            # 方法2：直接使用CorrectionService执行，绕过Celery
            correction_service = CorrectionService()
            result = correction_service.perform_correction(essay_id)
            logger.info(f"批改直接执行结果: {result}")
            
            return True
        except Exception as e:
            logger.error(f"批改任务执行失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False
            
    except Exception as e:
        logger.error(f"手动触发批改失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    finally:
        # 关闭数据库会话
        db.session.close()

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("手动批改任务执行成功！")
    else:
        logger.error("手动批改任务执行失败。")
        sys.exit(1) 