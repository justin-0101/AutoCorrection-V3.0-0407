#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
处理待批改作文的实用工具
用于自动检测和处理处于等待状态的作文
"""

import os
import sys
import logging
import uuid
from datetime import datetime
import time

# 确保系统路径正确
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, ROOT_DIR)

# 导入必要的模块
from flask import Flask
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.tasks.correction_tasks import process_essay_correction
from app.config import load_config
from app.extensions import db  # 从extensions导入db
from sqlalchemy.exc import SQLAlchemyError

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def create_minimal_app():
    """创建一个最小的Flask应用用于数据库操作"""
    # 创建最小Flask应用
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(load_config('default'))
    
    # 确保数据库目录存在
    db_dir = os.path.join(ROOT_DIR, 'instance')
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # 确保数据库文件存在
    db_path = os.path.join(db_dir, 'essay_correction.db')
    if not os.path.exists(db_path):
        open(db_path, 'a').close()
    
    # 设置数据库URI
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path.replace("\\", "/")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 设置为测试模式，这样SafeSQLAlchemy会重新初始化
    app.config['TESTING'] = True
    
    # 初始化db
    db.init_app(app)
    
    return app

def process_pending_corrections(limit=10):
    """
    处理待批改的作文
    
    Args:
        limit: 一次处理的最大数量
        
    Returns:
        bool: 处理是否成功
    """
    # 创建最小应用
    app = create_minimal_app()
    
    try:
        with app.app_context():
            # 查询处于待批改状态的作文
            pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING).limit(limit).all()
            
            if not pending_essays:
                logger.info("没有待处理的作文")
                return True
                
            logger.info(f"找到 {len(pending_essays)} 篇待处理的作文")
            
            processed_count = 0
            for essay in pending_essays:
                logger.info(f"准备处理作文 [essay_id={essay.id}, 标题='{essay.title}']")
                
                try:
                    # 使用事务保证操作的原子性
                    with db.session.begin_nested():
                        # 查找或创建对应的批改记录
                        correction = Correction.query.filter_by(essay_id=essay.id).first()
                        
                        if not correction:
                            logger.info(f"未找到作文 {essay.id} 的批改记录，创建新记录")
                            # 创建新的批改记录
                            correction = Correction(
                                essay_id=essay.id,
                                status=CorrectionStatus.PENDING,
                                created_at=datetime.now()
                            )
                            db.session.add(correction)
                            db.session.flush()  # 确保批改记录有ID
                        elif correction.status != CorrectionStatus.PENDING:
                            logger.warning(f"作文 {essay.id} 的批改记录状态为 {correction.status}，"
                                        f"而作文状态为 {essay.status}，跳过处理")
                            continue
                            
                        # 清理之前关联的任务ID
                        if correction.task_id:
                            logger.warning(f"批改记录 {correction.id} 已有任务ID: {correction.task_id}，将清除")
                            correction.task_id = None
                        
                        # 1. 先标记为处理中但使用临时状态
                        essay.status = EssayStatus.PROCESSING  # 临时状态
                        correction.status = CorrectionStatus.PROCESSING
                        db.session.flush()  # 仅在事务内提交
                        
                        # 生成唯一的任务ID
                        task_id = str(uuid.uuid4())
                        
                        # 2. 提交任务
                        logger.info(f"提交作文批改任务 [essay_id={essay.id}, task_id={task_id}]")
                        task = process_essay_correction.apply_async(
                            args=[essay.id],
                            task_id=task_id
                        )
                        
                        # 3. 任务提交成功后更新状态和任务ID
                        if task and task.id:
                            logger.info(f"任务提交成功 [essay_id={essay.id}, task_id={task.id}]")
                            
                            # 更新批改记录状态和任务ID
                            correction.task_id = task.id
                            correction.status = CorrectionStatus.CORRECTING
                            
                            # 更新作文状态
                            essay.status = EssayStatus.CORRECTING
                            
                            processed_count += 1
                            logger.info(f"成功更新作文状态为批改中 [essay_id={essay.id}, task_id={task.id}]")
                        else:
                            # 任务提交失败，回滚到PENDING状态
                            raise Exception(f"任务提交失败 [essay_id={essay.id}]")
                    
                    # 提交整个事务
                    db.session.commit()
                    
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"处理作文 {essay.id} 时出错: {str(e)}")
                    
                    # 确保状态回滚到PENDING
                    try:
                        with db.session.begin():
                            essay_refresh = Essay.query.get(essay.id)
                            correction_refresh = Correction.query.filter_by(essay_id=essay.id).first()
                            if essay_refresh:
                                essay_refresh.status = EssayStatus.PENDING
                            if correction_refresh:
                                correction_refresh.status = CorrectionStatus.PENDING
                                correction_refresh.task_id = None
                    except Exception as rollback_error:
                        logger.critical(f"回滚状态失败: {str(rollback_error)}")
                        
            logger.info(f"成功处理 {processed_count}/{len(pending_essays)} 篇作文")
            return True
    except Exception as e:
        logger.exception(f"处理待批改作文时出错: {str(e)}")
        return False

if __name__ == "__main__":
    while True:
        logger.info("开始处理待批改作文")
        try:
            success = process_pending_corrections()
            if success:
                logger.info("处理待批改作文完成，等待新的作文...")
            else:
                logger.error("处理待批改作文失败")
        except Exception as e:
            logger.exception(f"处理循环异常: {str(e)}")
        
        # 等待一段时间后继续检查
        time.sleep(30)  # 30秒后再次检查 