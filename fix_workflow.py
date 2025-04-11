#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改系统工作流修复工具
用于诊断和修复整个作文批改流程，确保所有组件协调工作
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("workflow_fix")

# 获取项目根目录
BASE_DIR = Path(__file__).parent.absolute()
logger.info(f"项目根目录: {BASE_DIR}")

def check_database_connection():
    """检查数据库连接是否正常"""
    logger.info("检查数据库连接...")
    try:
        from app.models.db import db
        from app import create_app
        
        app = create_app()
        with app.app_context():
            db.engine.connect()
            logger.info("数据库连接成功")
            return True
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return False

def check_redis_connection():
    """检查Redis连接是否正常"""
    logger.info("检查Redis连接...")
    try:
        from app.core.services.redis_service import RedisService
        
        redis = RedisService()
        redis.ping()
        logger.info("Redis连接成功")
        return True
    except Exception as e:
        logger.error(f"Redis连接失败: {str(e)}")
        return False

def check_ai_service():
    """检查AI服务是否正常"""
    logger.info("检查AI服务...")
    try:
        from app.core.services.container import container
        from app.core.ai import AIClientFactory
        
        # 初始化AI客户端工厂
        ai_client_factory = AIClientFactory()
        container.register('ai_client_factory', ai_client_factory)
        
        # 获取AI客户端
        ai_client = ai_client_factory.get_client()
        logger.info(f"AI服务初始化成功: {type(ai_client).__name__}")
        return True
    except Exception as e:
        logger.error(f"AI服务初始化失败: {str(e)}")
        return False

def fix_service_container():
    """修复服务容器"""
    logger.info("修复服务容器...")
    try:
        from app.core.services.container import container
        
        # 检查Redis服务
        try:
            redis_service = container.get('redis_service')
            if not redis_service:
                from app.core.services.redis_service import RedisService
                redis_service = RedisService()
                container.register('redis_service', redis_service)
                logger.info("Redis服务已注册到容器")
        except Exception as e:
            logger.error(f"注册Redis服务失败: {str(e)}")
        
        # 检查AI客户端工厂
        try:
            ai_client_factory = container.get('ai_client_factory')
            if not ai_client_factory:
                from app.core.ai import AIClientFactory
                ai_client_factory = AIClientFactory()
                container.register('ai_client_factory', ai_client_factory)
                logger.info("AI客户端工厂已注册到容器")
        except Exception as e:
            logger.error(f"注册AI客户端工厂失败: {str(e)}")
        
        # 检查批改服务
        try:
            correction_service = container.get('correction_service')
            if not correction_service:
                from app.core.correction.correction_service import CorrectionService
                correction_service = CorrectionService()
                container.register('correction_service', correction_service)
                logger.info("批改服务已注册到容器")
        except Exception as e:
            logger.error(f"注册批改服务失败: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"修复服务容器失败: {str(e)}")
        return False

def restart_celery_workers():
    """重启Celery工作进程"""
    logger.info("重启Celery工作进程...")
    
    # 首先停止现有进程
    if os.name == 'nt':  # Windows
        subprocess.run(['taskkill', '/F', '/IM', 'celery.exe'], 
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    else:  # Linux/Mac
        subprocess.run(['pkill', '-9', '-f', 'celery'], 
                    stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    
    time.sleep(2)  # 给进程时间完全终止
    
    # 启动Celery工作进程
    celery_script = os.path.join(BASE_DIR, 'scripts', 'start_celery.py')
    if os.path.exists(celery_script):
        logger.info(f"使用脚本启动Celery: {celery_script}")
        subprocess.Popen([sys.executable, celery_script], 
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Celery工作进程已启动")
        return True
    else:
        logger.error(f"Celery启动脚本不存在: {celery_script}")
        return False

def fix_celery_config():
    """修复Celery配置"""
    logger.info("修复Celery配置...")
    
    # 检查app/tasks/__init__.py
    tasks_init = os.path.join(BASE_DIR, 'app', 'tasks', '__init__.py')
    if not os.path.exists(tasks_init):
        logger.error(f"任务初始化文件不存在: {tasks_init}")
        return False
    
    with open(tasks_init, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 确保导入了celery_app
    if 'from app.tasks.celery_app import celery_app' not in content:
        logger.info("修复任务初始化文件，添加celery_app导入")
        with open(tasks_init, 'w', encoding='utf-8') as f:
            f.write('#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n"""\nCelery任务包\n用于注册和管理异步任务\n"""\n\n# 导入celery实例以便其他模块可以访问\nfrom app.tasks.celery_app import celery_app\n\n# 导入所有任务模块以确保它们被注册\nfrom app.tasks import correction_tasks\n\n__all__ = ["celery_app"]\n')
    
    # 修复start_celery.py
    celery_script = os.path.join(BASE_DIR, 'scripts', 'start_celery.py')
    if os.path.exists(celery_script):
        with open(celery_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 确保使用正确的Celery应用路径
        if "app.tasks:celery" in content:
            logger.info("修复Celery启动脚本，更新Celery应用路径")
            content = content.replace("app.tasks:celery", "app.tasks.celery_app:celery_app")
            with open(celery_script, 'w', encoding='utf-8') as f:
                f.write(content)
    
    logger.info("Celery配置修复完成")
    return True

def check_essay_processing():
    """检查作文处理流程"""
    logger.info("检查作文处理流程...")
    
    try:
        from app import create_app
        from app.models.db import db
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        
        app = create_app()
        with app.app_context():
            # 检查待处理的作文
            pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING.value).all()
            logger.info(f"发现 {len(pending_essays)} 篇待处理作文")
            
            # 检查处理中的作文
            correcting_essays = Essay.query.filter_by(status=EssayStatus.CORRECTING.value).all()
            logger.info(f"发现 {len(correcting_essays)} 篇处理中作文")
            
            # 检查已完成的作文
            completed_essays = Essay.query.filter_by(status=EssayStatus.COMPLETED.value).all()
            logger.info(f"发现 {len(completed_essays)} 篇已完成作文")
            
            # 检查批改记录
            corrections = Correction.query.all()
            logger.info(f"发现 {len(corrections)} 条批改记录")
            
            # 检查是否有批改记录与作文状态不匹配的情况
            mismatched = 0
            for correction in corrections:
                essay = Essay.query.get(correction.essay_id)
                if not essay:
                    logger.warning(f"批改记录 {correction.id} 对应的作文 {correction.essay_id} 不存在")
                    mismatched += 1
                    continue
                
                if correction.status == CorrectionStatus.COMPLETED.value and essay.status != EssayStatus.COMPLETED.value:
                    logger.warning(f"作文 {essay.id} 的批改记录显示已完成，但作文状态为 {essay.status}")
                    mismatched += 1
            
            logger.info(f"发现 {mismatched} 条不匹配的批改记录")
            
            return True
    except Exception as e:
        logger.error(f"检查作文处理流程失败: {str(e)}")
        return False

def process_pending_essays():
    """处理待处理的作文"""
    logger.info("处理待处理的作文...")
    
    try:
        from app import create_app
        from app.models.db import db
        from app.models.essay import Essay, EssayStatus
        from app.tasks.correction_tasks import process_essay_correction
        
        app = create_app()
        with app.app_context():
            # 获取所有待处理的作文
            pending_essays = Essay.query.filter_by(status=EssayStatus.PENDING.value).all()
            
            if not pending_essays:
                logger.info("没有待处理的作文")
                return True
            
            logger.info(f"开始处理 {len(pending_essays)} 篇待处理作文")
            
            for essay in pending_essays:
                try:
                    # 更新作文状态为处理中
                    essay.status = EssayStatus.CORRECTING.value
                    db.session.commit()
                    
                    # 提交到Celery任务队列
                    task = process_essay_correction.delay(essay.id)
                    logger.info(f"作文 {essay.id} 已提交到任务队列，任务ID: {task.id}")
                except Exception as e:
                    logger.error(f"处理作文 {essay.id} 时出错: {str(e)}")
                    # 回滚状态
                    essay.status = EssayStatus.PENDING.value
                    db.session.commit()
            
            logger.info("所有待处理作文已提交到任务队列")
            return True
    except Exception as e:
        logger.error(f"处理待处理作文失败: {str(e)}")
        return False

def fix_essay_status():
    """修复卡在错误状态的作文"""
    logger.info("修复卡在错误状态的作文...")
    
    try:
        from app import create_app
        from app.models.db import db
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        
        app = create_app()
        with app.app_context():
            # 获取所有状态为处理中但时间超过1小时的作文
            from datetime import datetime, timedelta
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            # 查找长时间处理中的作文
            stuck_essays = Essay.query.filter(
                Essay.status == EssayStatus.CORRECTING.value,
                Essay.updated_at < one_hour_ago
            ).all()
            
            if not stuck_essays:
                logger.info("没有卡在处理中状态的作文")
            else:
                logger.info(f"发现 {len(stuck_essays)} 篇卡在处理中状态的作文")
                
                for essay in stuck_essays:
                    # 将状态重置为待处理
                    essay.status = EssayStatus.PENDING.value
                    db.session.commit()
                    logger.info(f"作文 {essay.id} 状态已重置为待处理")
            
            # 检查批改记录与作文状态不匹配的情况
            corrections = Correction.query.filter_by(status=CorrectionStatus.COMPLETED.value).all()
            fixed_count = 0
            
            for correction in corrections:
                essay = Essay.query.get(correction.essay_id)
                if not essay:
                    logger.warning(f"批改记录 {correction.id} 对应的作文 {correction.essay_id} 不存在")
                    continue
                
                if essay.status != EssayStatus.COMPLETED.value:
                    # 更新作文状态为已完成
                    essay.status = EssayStatus.COMPLETED.value
                    db.session.commit()
                    logger.info(f"作文 {essay.id} 状态已更新为已完成，与批改记录匹配")
                    fixed_count += 1
            
            logger.info(f"修复了 {fixed_count} 篇作文状态")
            
            return True
    except Exception as e:
        logger.error(f"修复作文状态失败: {str(e)}")
        return False

def main():
    """执行所有修复步骤"""
    logger.info("=== 开始作文批改系统工作流修复 ===")
    
    # 1. 检查并修复数据库连接
    if check_database_connection():
        logger.info("数据库连接正常")
    else:
        logger.warning("数据库连接异常，请检查数据库配置")
    
    # 2. 检查并修复Redis连接
    if check_redis_connection():
        logger.info("Redis连接正常")
    else:
        logger.warning("Redis连接异常，请检查Redis服务是否启动")
    
    # 3. 修复服务容器
    if fix_service_container():
        logger.info("服务容器修复完成")
    else:
        logger.warning("服务容器修复失败，可能需要手动修复")
    
    # 4. 检查并修复AI服务
    if check_ai_service():
        logger.info("AI服务正常")
    else:
        logger.warning("AI服务异常，请检查AI服务配置")
    
    # 5. 修复Celery配置
    if fix_celery_config():
        logger.info("Celery配置修复完成")
    else:
        logger.warning("Celery配置修复失败，可能需要手动修复")
    
    # 6. 重启Celery工作进程
    if restart_celery_workers():
        logger.info("Celery工作进程已重启")
    else:
        logger.warning("Celery工作进程重启失败，请手动重启")
    
    # 7. 检查作文处理流程
    if check_essay_processing():
        logger.info("作文处理流程检查完成")
    else:
        logger.warning("作文处理流程检查失败，可能需要手动检查")
    
    # 8. 修复卡在错误状态的作文
    if fix_essay_status():
        logger.info("作文状态修复完成")
    else:
        logger.warning("作文状态修复失败，可能需要手动修复")
    
    # 9. 处理待处理的作文
    if process_pending_essays():
        logger.info("待处理作文已提交到任务队列")
    else:
        logger.warning("处理待处理作文失败，可能需要手动处理")
    
    logger.info("=== 作文批改系统工作流修复完成 ===")
    
    # 显示修复后的状态摘要
    try:
        from app import create_app
        from app.models.essay import Essay, EssayStatus
        
        app = create_app()
        with app.app_context():
            pending_count = Essay.query.filter_by(status=EssayStatus.PENDING.value).count()
            correcting_count = Essay.query.filter_by(status=EssayStatus.CORRECTING.value).count()
            completed_count = Essay.query.filter_by(status=EssayStatus.COMPLETED.value).count()
            failed_count = Essay.query.filter_by(status=EssayStatus.FAILED.value).count()
            
            print("\n作文状态摘要:")
            print(f"- 待处理作文: {pending_count} 篇")
            print(f"- 批改中作文: {correcting_count} 篇")
            print(f"- 已完成作文: {completed_count} 篇")
            print(f"- 批改失败作文: {failed_count} 篇")
            print("\n要提交待处理作文进行批改，请运行:")
            print("python scripts/utils/process_pending_corrections.py")
    except Exception as e:
        logger.error(f"获取状态摘要失败: {str(e)}")
    
    return True

if __name__ == "__main__":
    if main():
        print("\n修复完成! 系统工作流已恢复正常")
    else:
        print("\n修复过程遇到问题，请查看日志获取详细信息") 