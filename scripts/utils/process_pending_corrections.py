#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
处理待处理的批改任务
该脚本作为后台服务运行，持续监控并处理所有待批改的作文
"""

import os
import sys
from datetime import datetime
import time
import uuid
import logging
from logging.handlers import RotatingFileHandler

# 确保工作目录正确并添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
os.chdir(project_root)
sys.path.insert(0, project_root)

# 导入应用
from app import create_app
from app.models.correction import Correction, CorrectionStatus
from app.models.essay import Essay, EssayStatus
from app.tasks.correction_tasks import process_essay_correction
from app.tasks.celery_app import celery_app
from app.core.services.redis_service import RedisService
from app.core.ai import AIClientFactory
from app.core.services.container import container

def init_services():
    """初始化所需的服务"""
    # 初始化Redis服务
    redis_service = RedisService()
    container.register('redis_service', redis_service)
    
    # 初始化AI客户端工厂
    ai_client_factory = AIClientFactory()
    container.register('ai_client_factory', ai_client_factory)
    
    return redis_service, ai_client_factory

# 配置日志
def setup_logger():
    logger = logging.getLogger('correction_service')
    logger.setLevel(logging.INFO)
    
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 文件处理器
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'correction_service.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'  # 添加UTF-8编码设置
    )
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)  # 指定输出到标准输出
    console_handler.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def process_pending_corrections(logger):
    """处理所有待处理的批改任务"""
    with app.app_context():
        try:
            # 查找所有待处理的批改任务
            pending_corrections = Correction.query.filter_by(
                status=CorrectionStatus.PENDING.value
            ).all()
            
            if not pending_corrections:
                logger.debug("当前没有待处理的批改任务")
                return 0
            
            processed_count = 0
            for correction in pending_corrections:
                try:
                    essay_id = correction.essay_id
                    essay = Essay.query.get(essay_id)
                    
                    if not essay:
                        logger.error(f"未找到作文 ID={essay_id}，跳过")
                        continue
                    
                    logger.info(f"处理作文 ID={essay_id}, 标题: {essay.title}")
                    
                    # 更新状态为correcting
                    correction.status = CorrectionStatus.CORRECTING.value
                    essay.status = EssayStatus.CORRECTING.value
                    
                    # 生成任务ID
                    task_id = str(uuid.uuid4())
                    correction.task_id = task_id
                    
                    # 提交到数据库
                    from app.models.db import db
                    db.session.commit()
                    
                    # 发送到Celery任务队列
                    task_result = process_essay_correction.delay(essay_id)
                    logger.info(f"任务已提交，任务ID: {task_result.id}")
                    
                    # 保存实际的Celery任务ID
                    correction.task_id = task_result.id
                    db.session.commit()
                    
                    processed_count += 1
                    logger.info(f"成功: 作文 ID={essay_id} 已提交到任务队列")
                    
                except Exception as e:
                    logger.error(f"处理作文ID={essay_id}时出错: {str(e)}")
                    
                    # 更新状态为失败
                    correction.status = CorrectionStatus.FAILED.value
                    correction.error_message = f"提交任务失败: {str(e)}"
                    essay.status = EssayStatus.FAILED.value
                    db.session.commit()
            
            return processed_count
            
        except Exception as e:
            logger.error(f"处理批改任务时发生错误: {str(e)}")
            return 0

def main():
    """主函数，持续运行并处理待批改作文"""
    logger = setup_logger()
    logger.info("批改服务启动")
    
    # 初始化应用
    global app
    app = create_app()
    
    # 初始化服务
    logger.info("正在初始化服务...")
    redis_service, ai_client_factory = init_services()
    logger.info("服务初始化完成")
    
    check_interval = 10  # 检查间隔（秒）
    
    try:
        while True:
            try:
                processed_count = process_pending_corrections(logger)
                if processed_count > 0:
                    logger.info(f"本次处理了 {processed_count} 个待批改作文")
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("收到停止信号，服务正在停止...")
                break
            except Exception as e:
                logger.error(f"服务运行出错: {str(e)}")
                time.sleep(check_interval)
    
    finally:
        logger.info("批改服务已停止")

if __name__ == "__main__":
    main() 