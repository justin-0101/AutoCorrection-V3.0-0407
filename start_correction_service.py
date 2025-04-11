#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动批改服务测试
此脚本用于测试修复后的批改服务功能
"""

import os
import sys
import logging
import time
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('correction_test')

# 确保工作目录正确
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

def test_correction_service():
    """测试批改服务功能"""
    try:
        # 导入Flask应用
        from app import create_app
        from app.models.db import db
        from app.models.essay import Essay
        from app.models.essay_status import EssayStatus
        from app.core.correction.correction_service import CorrectionService
        
        app = create_app()
        
        with app.app_context():
            logger.info("Flask应用上下文已创建")
            
            # 检查数据库连接
            logger.info(f"数据库URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
            
            # 尝试获取批改服务
            correction_service = CorrectionService()
            logger.info("批改服务实例创建成功")
            
            # 检查待批改的作文
            pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING.value).all()
            logger.info(f"发现 {len(pending_essays)} 篇待批改的作文")
            
            # 如果有待批改的作文，尝试批改第一篇
            if pending_essays:
                essay = pending_essays[0]
                logger.info(f"尝试批改作文: ID={essay.id}, 标题={essay.title}")
                
                try:
                    # 执行批改
                    result = correction_service.perform_correction(essay.id)
                    logger.info(f"批改结果: {result}")
                    
                    # 检查批改后的状态
                    essay = Essay.query.get(essay.id)
                    logger.info(f"批改后的作文状态: {essay.status}")
                    
                except Exception as e:
                    logger.error(f"批改作文时出错: {str(e)}", exc_info=True)
            else:
                logger.info("没有待批改的作文，创建一篇测试作文")
                
                # 创建一篇测试作文
                essay = Essay(
                    title="测试作文",
                    content="这是一篇测试作文，用于验证批改服务功能。内容需要足够长才能进行批改。" * 10,
                    user_id=1,
                    status=EssayStatus.PENDING.value,
                    essay_type="narrative",
                    grade="high_school",
                    source="test",
                    word_count=200,
                    created_at=datetime.now()
                )
                db.session.add(essay)
                db.session.commit()
                
                logger.info(f"创建测试作文成功: ID={essay.id}")
                
                # 尝试批改
                result = correction_service.perform_correction(essay.id)
                logger.info(f"批改结果: {result}")
                
                # 检查批改后的状态
                essay = Essay.query.get(essay.id)
                logger.info(f"批改后的作文状态: {essay.status}")
    
    except Exception as e:
        logger.error(f"测试批改服务时出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("开始测试批改服务...")
    test_correction_service()
    logger.info("测试完成") 