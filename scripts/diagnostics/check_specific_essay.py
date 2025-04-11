#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_specific_essay(essay_id):
    """检查特定ID的作文及其批改记录的详细状态"""
    app = create_app()
    with app.app_context():
        try:
            # 查询特定ID的作文
            essay = db.session.query(Essay).filter(Essay.id == essay_id).first()
            
            if not essay:
                logger.error(f"未找到ID为 {essay_id} 的作文")
                return
            
            # 打印作文详细信息
            logger.info(f"===== 作文ID: {essay.id} =====")
            logger.info(f"标题: {essay.title}")
            logger.info(f"内容前100字符: {essay.content[:100]}...")
            
            # 检查状态是枚举还是字符串
            if hasattr(essay.status, 'name'):
                status_text = essay.status.name
            else:
                status_text = str(essay.status)
            
            logger.info(f"状态: {status_text}")
            logger.info(f"提交时间: {essay.created_at}")
            logger.info(f"更新时间: {essay.updated_at}")
            
            # 查询相关的批改记录
            corrections = db.session.query(Correction).filter(Correction.essay_id == essay_id).all()
            
            if not corrections:
                logger.info(f"作文ID {essay_id} 没有相关批改记录")
            else:
                logger.info(f"找到 {len(corrections)} 条批改记录:")
                
                for idx, correction in enumerate(corrections, 1):
                    logger.info(f"  -- 批改记录 #{idx} (ID: {correction.id}) --")
                    
                    # 检查状态是枚举还是字符串
                    if hasattr(correction.status, 'name'):
                        corr_status_text = correction.status.name
                    else:
                        corr_status_text = str(correction.status)
                    
                    logger.info(f"  状态: {corr_status_text}")
                    if hasattr(correction, 'task_id') and correction.task_id:
                        logger.info(f"  任务ID: {correction.task_id}")
                    logger.info(f"  创建时间: {correction.created_at}")
                    logger.info(f"  更新时间: {correction.updated_at}")
                    
                    if hasattr(correction, 'result') and correction.result:
                        result_str = str(correction.result)
                        if len(result_str) > 100:
                            result_str = result_str[:100] + "..."
                        logger.info(f"  批改结果: {result_str}")
                    elif hasattr(correction, 'results') and correction.results:
                        result_str = str(correction.results)
                        if len(result_str) > 100:
                            result_str = result_str[:100] + "..."
                        logger.info(f"  批改结果: {result_str}")
                    else:
                        logger.info("  批改结果: 无")
            
            logger.info("===== 检查完成 =====")
            
        except Exception as e:
            logger.error(f"检查作文时发生错误: {str(e)}")

if __name__ == "__main__":
    try:
        # 获取命令行参数，如果没有提供，则使用默认值20
        if len(sys.argv) > 1:
            try:
                essay_id = int(sys.argv[1])
                logger.info(f"正在检查作文ID: {essay_id}")
            except ValueError:
                logger.error("提供的作文ID无效，必须是整数")
                sys.exit(1)
        else:
            essay_id = 20
            logger.info(f"未提供作文ID，使用默认值: {essay_id}")
        
        check_specific_essay(essay_id)
    except Exception as e:
        logger.error(f"程序执行过程中发生未处理异常: {str(e)}")
        sys.exit(1) 