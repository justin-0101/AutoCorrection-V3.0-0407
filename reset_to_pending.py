#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
将所有CORRECTING状态的作文重置为PENDING状态的脚本
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('reset_essays')

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus
from app.models.essay import Essay, EssayStatus
from app.models.db import db

def reset_essays():
    """将所有CORRECTING状态的作文重置为PENDING状态"""
    app = create_app()
    with app.app_context():
        # 查找所有CORRECTING状态的作文
        correcting_essays = Essay.query.filter_by(status=EssayStatus.CORRECTING.value).all()
        logger.info(f"找到 {len(correcting_essays)} 篇处于CORRECTING状态的作文")
        
        reset_count = 0
        for essay in correcting_essays:
            # 查找对应的批改记录
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            
            if not correction:
                logger.warning(f"作文ID={essay.id} 没有对应的批改记录，创建新记录")
                correction = Correction(
                    essay_id=essay.id,
                    status=CorrectionStatus.PENDING.value
                )
                db.session.add(correction)
                essay.status = EssayStatus.PENDING.value
                reset_count += 1
                continue
                
            # 更新批改记录和作文状态为PENDING
            logger.info(f"重置作文: ID={essay.id}, 标题={essay.title[:20]}...")
            correction.status = CorrectionStatus.PENDING.value
            essay.status = EssayStatus.PENDING.value
            
            # 清除任务ID
            if correction.task_id:
                logger.info(f"清除批改记录任务ID: {correction.task_id}")
                correction.task_id = None
                
            reset_count += 1
            
        # 提交更改
        if reset_count > 0:
            db.session.commit()
            logger.info(f"已重置 {reset_count} 篇作文状态为PENDING")
        else:
            logger.info("没有需要重置的作文")
            
        return reset_count

if __name__ == "__main__":
    try:
        reset_count = reset_essays()
        logger.info(f"脚本执行完成，共重置了 {reset_count} 篇作文状态")
    except Exception as e:
        logger.error(f"脚本执行出错: {str(e)}")
        sys.exit(1) 