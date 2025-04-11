#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查看作文状态和批改记录的脚本
"""

import os
import sys
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def check_essay_status():
    """检查作文状态和批改记录"""
    try:
        # 导入所需模块
        from app import create_app
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        from app.models.db import db
        
        app = create_app()
        
        with app.app_context():
            # 查询所有作文及其批改状态
            logger.info("===== 作文状态报告 =====")
            
            # 统计各状态的作文数量
            total_essays = db.session.query(Essay).count()
            logger.info(f"作文总数: {total_essays}")
            
            for status in EssayStatus:
                count = db.session.query(Essay).filter_by(status=status).count()
                logger.info(f"状态 '{status}' 的作文数量: {count}")
            
            # 查询最近的作文详情
            recent_essays = db.session.query(Essay).order_by(Essay.created_at.desc()).limit(5).all()
            
            logger.info("\n===== 最近5篇作文详情 =====")
            for essay in recent_essays:
                logger.info(f"作文ID: {essay.id}")
                logger.info(f"  标题: {essay.title}")
                logger.info(f"  状态: {essay.status}")
                logger.info(f"  创建时间: {essay.created_at}")
                
                # 查询对应的批改记录
                correction = db.session.query(Correction).filter_by(essay_id=essay.id).first()
                if correction:
                    logger.info(f"  批改状态: {correction.status}")
                    logger.info(f"  批改任务ID: {correction.task_id}")
                    
                    if hasattr(correction, 'error_message') and correction.error_message:
                        logger.info(f"  错误信息: {correction.error_message}")
                else:
                    logger.info("  没有找到对应的批改记录")
                    
                logger.info("---------------------")
            
            return True
    except Exception as e:
        logger.error(f"检查作文状态时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    check_essay_status() 