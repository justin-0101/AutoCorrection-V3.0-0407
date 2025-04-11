#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试状态一致性检查和修复任务
直接调用check_and_fix_inconsistent_statuses任务函数
"""

import os
import sys
import logging
from datetime import datetime

# 确保可以导入应用模块
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.tasks.maintenance_tasks import check_and_fix_inconsistent_statuses

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def run_check_and_fix():
    """运行状态一致性检查和修复任务"""
    logger.info("开始运行状态一致性检查和修复任务...")
    
    app = create_app()
    with app.app_context():
        # 直接调用函数
        result = check_and_fix_inconsistent_statuses()
        
        # 输出结果
        logger.info(f"任务执行结果: {result}")
        
        if isinstance(result, dict):
            if result.get('status') == 'success':
                logger.info(f"状态检查完成: 发现 {result.get('inconsistent_count', 0)} 条不一致状态, "
                           f"修复了 {result.get('fixed_count', 0)} 条")
                logger.info(f"滞留任务检查: 发现 {result.get('stale_count', 0)} 条滞留任务, "
                           f"处理了 {result.get('stale_fixed_count', 0)} 条")
            else:
                logger.error(f"任务执行失败: {result.get('error', '未知错误')}")
        else:
            logger.warning(f"任务返回了意外的结果类型: {type(result)}")
    
    logger.info("状态一致性检查和修复任务完成")

if __name__ == "__main__":
    run_check_and_fix() 