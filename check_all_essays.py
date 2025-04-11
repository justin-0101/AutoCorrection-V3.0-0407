#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查所有作文状态的脚本
列出所有作文和对应的批改记录状态
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
logger = logging.getLogger('check_essays')

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus
from app.models.essay import Essay, EssayStatus
from app.models.db import db

def check_essays():
    """检查所有作文和批改记录状态"""
    app = create_app()
    with app.app_context():
        # 获取所有作文
        essays = Essay.query.all()
        logger.info(f"总共找到 {len(essays)} 篇作文")
        
        # 统计每种状态的作文数量
        status_counts = {}
        for essay in essays:
            status = essay.status
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        # 输出统计信息
        logger.info("作文状态统计:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}篇")
            
        # 检查每篇作文的批改记录
        logger.info("\n检查每篇作文和对应的批改记录:")
        for essay in essays:
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            
            if correction:
                logger.info(f"作文ID: {essay.id}, 标题: {essay.title[:20]}..., 作文状态: {essay.status}, 批改记录状态: {correction.status}")
            else:
                logger.info(f"作文ID: {essay.id}, 标题: {essay.title[:20]}..., 作文状态: {essay.status}, 无对应批改记录")
        
        # 查找不一致的记录
        logger.info("\n检查状态不一致的记录:")
        inconsistent_count = 0
        for essay in essays:
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            
            if not correction:
                continue
                
            if essay.status == EssayStatus.PENDING.value and correction.status != CorrectionStatus.PENDING.value:
                logger.warning(f"不一致: 作文ID={essay.id} 状态为PENDING，但批改记录状态为{correction.status}")
                inconsistent_count += 1
            elif essay.status == EssayStatus.CORRECTING.value and correction.status != CorrectionStatus.CORRECTING.value:
                logger.warning(f"不一致: 作文ID={essay.id} 状态为CORRECTING，但批改记录状态为{correction.status}")
                inconsistent_count += 1
                
        if inconsistent_count == 0:
            logger.info("未发现状态不一致的记录")
            
        return len(essays)

if __name__ == "__main__":
    try:
        essay_count = check_essays()
        logger.info(f"脚本执行完成，总共检查了 {essay_count} 篇作文")
    except Exception as e:
        logger.error(f"脚本执行出错: {str(e)}")
        sys.exit(1) 