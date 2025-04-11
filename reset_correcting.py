#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重置所有正在批改中的作文状态
将所有当前处于CORRECTING状态的作文重置为PENDING状态
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import argparse

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = script_dir  # 当前脚本就在项目根目录
sys.path.insert(0, project_root)

# 配置日志
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

# 创建logger
logger = logging.getLogger('reset_correcting')
logger.setLevel(logging.INFO)

# 文件处理器
file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'reset_correcting.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# 控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 格式化器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

def reset_correcting_essays():
    """
    重置所有处于CORRECTING状态的作文为PENDING状态
    """
    from app import create_app
    from app.models.essay import Essay, EssayStatus
    from app.models.correction import Correction, CorrectionStatus
    from app.models.db import db

    app = create_app()

    with app.app_context():
        try:
            # 查找所有处于CORRECTING状态的作文
            correcting_essays = Essay.query.filter_by(
                status=EssayStatus.CORRECTING.value
            ).all()

            if not correcting_essays:
                logger.info("没有找到正在批改中的作文")
                return 0

            reset_count = 0
            for essay in correcting_essays:
                try:
                    essay_id = essay.id
                    old_status = essay.status
                    
                    # 重置作文状态为PENDING
                    essay.status = EssayStatus.PENDING.value
                    
                    # 查找对应的批改记录
                    corrections = Correction.query.filter_by(essay_id=essay_id).all()
                    for correction in corrections:
                        if correction.status == CorrectionStatus.CORRECTING.value:
                            # 重置批改记录状态为PENDING
                            correction.status = CorrectionStatus.PENDING.value
                            # 清除任务ID
                            correction.task_id = None
                            logger.info(f"重置批改记录: ID={correction.id}, 作文ID={essay_id}, 旧状态={correction.status}")
                    
                    # 提交更改
                    db.session.commit()
                    
                    reset_count += 1
                    logger.info(f"重置作文: ID={essay_id}, 标题={essay.title}, 旧状态={old_status}")
                    
                except Exception as e:
                    logger.error(f"重置作文ID={essay_id}时出错: {str(e)}")
                    db.session.rollback()

            logger.info(f"总共重置了 {reset_count} 篇作文")
            return reset_count
            
        except Exception as e:
            logger.error(f"重置作文状态时发生错误: {str(e)}")
            return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重置所有正在批改中的作文状态")
    args = parser.parse_args()
    
    try:
        logger.info("开始重置正在批改中的作文...")
        reset_count = reset_correcting_essays()
        logger.info(f"重置完成，共重置 {reset_count} 篇作文")
    except KeyboardInterrupt:
        logger.info("用户中断，已停止")
    except Exception as e:
        logger.error(f"发生未知错误: {str(e)}")
        sys.exit(1) 