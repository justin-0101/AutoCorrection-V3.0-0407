#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复批改记录状态脚本
查找作文状态为PENDING但批改记录状态不是PENDING的记录，并修复它们
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
logger = logging.getLogger('fix_correction')

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus
from app.models.essay import Essay, EssayStatus
from app.models.db import db

def fix_correction_status():
    """修复批改记录状态"""
    app = create_app()
    with app.app_context():
        # 1. 检查作文状态和批改记录状态
        logger.info("开始检查作文和批改记录状态...")
        
        # 查找所有PENDING状态的作文
        pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING.value).all()
        logger.info(f"找到 {len(pending_essays)} 篇PENDING状态的作文")
        
        fixed_count = 0
        for essay in pending_essays:
            # 查找对应的批改记录
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            
            if not correction:
                logger.warning(f"作文ID={essay.id} 没有对应的批改记录，创建新记录")
                correction = Correction(
                    essay_id=essay.id,
                    status=CorrectionStatus.PENDING.value
                )
                db.session.add(correction)
                fixed_count += 1
                continue
                
            # 检查批改记录状态，如果不是PENDING，则修复
            if correction.status != CorrectionStatus.PENDING.value:
                logger.info(f"修复批改记录: ID={correction.id}, 作文ID={essay.id}, 当前状态={correction.status}")
                correction.status = CorrectionStatus.PENDING.value
                fixed_count += 1
        
        # 提交更改
        if fixed_count > 0:
            db.session.commit()
            logger.info(f"已修复 {fixed_count} 条批改记录")
        else:
            logger.info("所有批改记录状态正常，无需修复")
        
        # 显示最终状态
        pending_corrections = Correction.query.filter_by(status=CorrectionStatus.PENDING.value).all()
        logger.info(f"当前共有 {len(pending_corrections)} 条PENDING状态的批改记录")
        
        return fixed_count

if __name__ == "__main__":
    try:
        fixed_count = fix_correction_status()
        logger.info(f"脚本执行完成，修复了 {fixed_count} 条记录")
    except Exception as e:
        logger.error(f"脚本执行出错: {str(e)}")
        sys.exit(1) 