#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重置所有非完成状态的作文到PENDING状态
"""

import os
import sys
import logging
from sqlalchemy.exc import SQLAlchemyError

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def reset_all_essays():
    """重置所有非完成的作文和批改记录到PENDING状态"""
    try:
        # 导入必要的模块
        from app import create_app
        from app.models.db import db
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        
        app = create_app()
        
        with app.app_context():
            # 获取所有非完成状态的作文
            non_completed_essays = db.session.query(Essay).filter(
                Essay.status != EssayStatus.COMPLETED.value,
                Essay.status != EssayStatus.ARCHIVED.value
            ).all()
            
            logger.info(f"找到 {len(non_completed_essays)} 篇非完成状态的作文")
            
            # 重置作文状态
            essay_count = 0
            for essay in non_completed_essays:
                old_status = essay.status
                essay.status = EssayStatus.PENDING.value
                essay_count += 1
                logger.info(f"重置作文 ID={essay.id}, 从 {old_status} 到 {essay.status}")
            
            # 提交更改
            db.session.commit()
            logger.info(f"已重置 {essay_count} 篇作文状态")
            
            # 获取所有非完成状态的批改记录
            non_completed_corrections = db.session.query(Correction).filter(
                Correction.status != CorrectionStatus.COMPLETED.value
            ).all()
            
            logger.info(f"找到 {len(non_completed_corrections)} 条非完成状态的批改记录")
            
            # 重置批改记录状态
            correction_count = 0
            for correction in non_completed_corrections:
                old_status = correction.status
                correction.status = CorrectionStatus.PENDING.value
                correction.task_id = None  # 清除任务ID以便重新提交
                correction_count += 1
                logger.info(f"重置批改记录 ID={correction.id}, 从 {old_status} 到 {correction.status}")
            
            # 提交更改
            db.session.commit()
            logger.info(f"已重置 {correction_count} 条批改记录状态")
            
            # 查找所有没有批改记录的作文
            all_essays = db.session.query(Essay).all()
            essays_without_correction = []
            
            for essay in all_essays:
                correction = db.session.query(Correction).filter_by(essay_id=essay.id).first()
                if not correction:
                    essays_without_correction.append(essay)
            
            # 为没有批改记录的作文创建批改记录
            if essays_without_correction:
                logger.info(f"发现 {len(essays_without_correction)} 篇作文没有对应的批改记录")
                for essay in essays_without_correction:
                    new_correction = Correction(
                        essay_id=essay.id,
                        status=CorrectionStatus.PENDING.value
                    )
                    db.session.add(new_correction)
                    logger.info(f"为作文 ID={essay.id} 创建了新的批改记录")
                
                # 提交更改
                db.session.commit()
            
            # 验证修复结果
            pending_essays = db.session.query(Essay).filter_by(status=EssayStatus.PENDING.value).count()
            pending_corrections = db.session.query(Correction).filter_by(status=CorrectionStatus.PENDING.value).count()
            
            logger.info(f"当前系统中共有 {pending_essays} 篇等待批改的作文")
            logger.info(f"当前系统中共有 {pending_corrections} 条等待处理的批改记录")
            
            return True
    
    except SQLAlchemyError as e:
        logger.error(f"数据库操作错误: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"重置作文状态时出错: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("开始重置所有非完成状态的作文...")
    success = reset_all_essays()
    if success:
        logger.info("重置操作完成")
    else:
        logger.error("重置操作失败") 