#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务注册修复脚本
修复AI客户端工厂注册和应用上下文相关问题
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# 确保工作目录正确并添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# 设置日志记录
def setup_logger():
    logger = logging.getLogger('service_fix')
    logger.setLevel(logging.INFO)
    
    # 创建日志目录
    log_dir = os.path.join(script_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 文件处理器
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'service_fix.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
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

def main():
    logger = setup_logger()
    logger.info("开始修复服务注册和数据库连接问题...")
    
    # 导入应用和关键组件
    from app import create_app
    from app.core.ai import AIClientFactory
    from app.core.services.container import container, ServiceScope
    from app.core.correction.ai_corrector import AICorrectionService
    from app.models.essay import Essay, EssayStatus
    from app.core.services.redis_service import RedisService
    
    # 创建应用实例
    app = create_app()
    
    with app.app_context():
        logger.info("获取数据库URI...")
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'unknown')
        logger.info(f"当前数据库URI: {db_uri}")
        
        # 清除并重新注册服务
        logger.info("清除并重新注册所有服务...")
        # 使用reset方法清空服务容器
        container.reset()
        logger.info("服务容器已重置")
        
        # 重新注册关键服务
        logger.info("重新注册AI客户端工厂...")
        ai_client_factory = AIClientFactory()
        container.register('ai_client_factory', ai_client_factory, ServiceScope.SINGLETON)
        logger.info("已注册AI客户端工厂")
        
        # 注册Redis服务
        logger.info("注册Redis服务...")
        redis_service = RedisService()
        container.register('redis_service', redis_service, ServiceScope.SINGLETON)
        logger.info("已注册Redis服务")
        
        # 注册批改服务
        logger.info("注册批改服务...")
        correction_service = AICorrectionService()
        container.register('correction_service', correction_service, ServiceScope.SINGLETON)
        logger.info("已注册批改服务")
        
        # 初始化服务容器
        container.initialize()
        
        # 验证注册
        if container.has('ai_client_factory'):
            logger.info("验证: AI客户端工厂注册成功")
        else:
            logger.error("验证失败: AI客户端工厂注册未成功")
        
        # 修复卡在CORRECTING状态但实际未处理的作文
        logger.info("修复卡在CORRECTING状态的作文...")
        try:
            from app.models.db import db
            from app.models.correction import Correction, CorrectionStatus
            
            correcting_essays = Essay.query.filter_by(status=EssayStatus.CORRECTING.value).all()
            logger.info(f"找到 {len(correcting_essays)} 篇处于CORRECTING状态的作文")
            
            fixed_count = 0
            for essay in correcting_essays:
                correction = Correction.query.filter_by(essay_id=essay.id).first()
                
                if not correction:
                    # 创建新的批改记录
                    logger.info(f"为作文 ID={essay.id} 创建缺失的批改记录")
                    correction = Correction(
                        essay_id=essay.id,
                        status=CorrectionStatus.PENDING.value
                    )
                    db.session.add(correction)
                elif correction.status == CorrectionStatus.CORRECTING.value:
                    # 重置到待处理状态
                    logger.info(f"重置作文 ID={essay.id} 和对应批改记录的状态为PENDING")
                    correction.status = CorrectionStatus.PENDING.value
                
                # 重置作文状态
                essay.status = EssayStatus.PENDING.value
                fixed_count += 1
            
            db.session.commit()
            logger.info(f"成功修复 {fixed_count} 篇作文状态")
            
        except Exception as e:
            logger.error(f"修复作文状态时出错: {str(e)}")
        
        # 检查数据库中是否有作文但没有对应的批改记录
        logger.info("检查缺失批改记录的作文...")
        try:
            all_essays = Essay.query.all()
            missing_correction_count = 0
            
            for essay in all_essays:
                correction = Correction.query.filter_by(essay_id=essay.id).first()
                if not correction:
                    logger.info(f"为作文 ID={essay.id} 创建缺失的批改记录")
                    correction = Correction(
                        essay_id=essay.id,
                        status=CorrectionStatus.PENDING.value
                    )
                    db.session.add(correction)
                    essay.status = EssayStatus.PENDING.value
                    missing_correction_count += 1
            
            if missing_correction_count > 0:
                db.session.commit()
                logger.info(f"成功为 {missing_correction_count} 篇作文创建缺失的批改记录")
            else:
                logger.info("未发现缺失批改记录的作文")
                
        except Exception as e:
            logger.error(f"检查缺失批改记录时出错: {str(e)}")
    
    logger.info("服务修复完成!")
    print("服务修复完成。请重启所有服务以应用更改。")

if __name__ == "__main__":
    main() 