#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复数据库中损坏的作文数据
解决自动批改服务中的'NoneType' object has no attribute 'id'错误
"""

import os
import sys
import logging
from datetime import datetime
import traceback

# 确保系统路径正确
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def create_minimal_app():
    """创建一个最小的Flask应用用于数据库操作"""
    try:
        from flask import Flask
        from app.config import load_config
        from app.extensions import db
        
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
        
        # 初始化db
        db.init_app(app)
        
        return app
    except Exception as e:
        logger.error(f"创建Flask应用失败: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def fix_empty_essays():
    """修复数据库中损坏的作文数据"""
    try:
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        from app.extensions import db
        
        # 创建最小应用
        app = create_minimal_app()
        if not app:
            logger.error("创建应用失败，无法继续修复")
            return False
            
        with app.app_context():
            # 1. 检查并显示作文表信息
            total_essays = Essay.query.count()
            pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING).count()
            
            logger.info(f"数据库中共有 {total_essays} 篇作文，其中 {pending_essays} 篇待处理")
            
            # 2. 检查损坏的PENDING状态作文（没有必须属性的记录）
            corrupt_essays = []
            pending_essays_list = Essay.query.filter_by(status=EssayStatus.PENDING).all()
            
            for essay in pending_essays_list:
                if essay is None:
                    logger.warning("发现空的作文对象")
                    corrupt_essays.append(None)
                    continue
                    
                try:
                    # 检查必要属性
                    required_attrs = ['id', 'title', 'content', 'user_id', 'created_at']
                    missing_attrs = []
                    
                    for attr in required_attrs:
                        if not hasattr(essay, attr) or getattr(essay, attr) is None:
                            missing_attrs.append(attr)
                    
                    if missing_attrs:
                        logger.warning(f"作文 ID {essay.id if hasattr(essay, 'id') else '未知'} 缺少以下属性: {', '.join(missing_attrs)}")
                        corrupt_essays.append(essay)
                except Exception as e:
                    logger.error(f"检查作文属性时出错: {str(e)}")
                    corrupt_essays.append(essay)
            
            logger.info(f"发现 {len(corrupt_essays)} 篇损坏的作文")
            
            # 3. 修复损坏的作文记录
            fixed_count = 0
            for essay in corrupt_essays:
                try:
                    if essay is None:
                        # 无法修复None对象，跳过
                        continue
                        
                    with db.session.begin():
                        essay_id = essay.id if hasattr(essay, 'id') else None
                        logger.info(f"尝试修复作文 ID: {essay_id}")
                        
                        if essay_id:
                            # 检查是否有关联的批改记录
                            corrections = Correction.query.filter_by(essay_id=essay_id).all()
                            
                            # 删除关联的批改记录
                            for correction in corrections:
                                logger.info(f"删除关联的批改记录 ID: {correction.id}")
                                db.session.delete(correction)
                            
                            # 更新作文状态为失败，避免再次处理
                            essay.status = EssayStatus.FAILED
                            essay.error_message = "作文数据不完整，已被系统标记为失败"
                            db.session.flush()
                            
                            fixed_count += 1
                            logger.info(f"成功修复作文 ID: {essay_id}")
                except Exception as e:
                    logger.error(f"修复作文时出错: {str(e)}")
                    db.session.rollback()
            
            # 4. 提交所有更改
            db.session.commit()
            logger.info(f"成功修复 {fixed_count} 篇损坏的作文")
            
            # 5. 清理None对象（不应存在，但以防万一）
            # 这一步可能无法完成，因为None对象无法通过ORM访问
            logger.info("检查是否还有待处理的作文...")
            pending_count = Essay.query.filter_by(status=EssayStatus.PENDING).count()
            logger.info(f"修复后还有 {pending_count} 篇待处理的作文")
            
            return True
    except Exception as e:
        logger.error(f"修复过程中出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("开始修复数据库中损坏的作文...")
    
    success = fix_empty_essays()
    
    if success:
        logger.info("数据库修复完成")
    else:
        logger.error("数据库修复失败")
        sys.exit(1) 