#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试作文批改功能
提交一篇测试作文并监控批改状态
"""

import os
import sys
import time
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# 导入项目模块
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def submit_test_essay():
    """提交测试作文并返回作文ID"""
    # 在函数内部导入模块，避免潜在的循环引用问题
    from app import create_app
    from app.models.essay import EssayStatus, EssaySourceType
    from app.models.correction import CorrectionStatus
    
    app = create_app()
    with app.app_context():
        try:
            # 测试用户ID
            user_id = 1
            
            # 测试作文内容
            title = f"测试作文 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            content = """
            The Importance of Environmental Protection

            Environmental protection has become a vital issue in the modern world. As our population grows and technology advances, we face increasing challenges in maintaining a healthy planet. This essay explores the importance of environmental protection and suggests ways individuals can contribute to a more sustainable future.

            First, environmental protection is essential for human health. Clean air, water, and soil are necessary for our survival. Pollution leads to respiratory diseases, contaminated drinking water causes illnesses, and toxic soils affect the safety of our food supply. By protecting our environment, we are also protecting ourselves.

            Second, biodiversity is crucial for ecosystem stability. Each species plays a unique role in maintaining the balance of nature. When species become extinct due to human activities, these delicate systems can collapse, leading to unpredictable consequences that may affect our food supply, climate regulation, and disease control.

            Third, environmental protection is economically beneficial in the long term. While some argue that environmental regulations are costly, the expenses of cleaning up pollution, treating environment-related illnesses, and dealing with natural disasters caused by climate change far outweigh the costs of prevention.

            What can individuals do to contribute? Simple daily actions can make a significant difference. Reducing plastic use, conserving water and energy, choosing sustainable products, and supporting environmentally friendly policies are all effective ways to help. Additionally, raising awareness and educating others about environmental issues can create a ripple effect of positive change.

            In conclusion, environmental protection is not just about saving distant forests or exotic animals; it is about ensuring a healthy, sustainable future for ourselves and coming generations. By taking action now, we can help create a world where people and nature thrive together.
            """
            
            # 使用数据库直接创建作文和批改记录，避免使用EssayService
            from app.models.db import db
            from app.models.essay import Essay
            from app.models.correction import Correction
            
            with db.session.begin():
                # 创建新作文记录
                essay = Essay(
                    user_id=user_id,
                    title=title,
                    content=content,
                    word_count=len(content),
                    source_type=EssaySourceType.text.value,
                    grade="高中",
                    author_name="测试用户",
                    is_public=True,
                    status=EssayStatus.PENDING,
                    created_at=datetime.now()
                )
                
                db.session.add(essay)
                db.session.flush()  # 获取essay.id
                essay_id = essay.id
                
                # 创建批改记录
                correction = Correction(
                    essay_id=essay_id,
                    status=CorrectionStatus.PENDING,
                    created_at=datetime.now()
                )
                
                db.session.add(correction)
            
            logger.info(f"测试作文已创建，ID: {essay_id}")
            
            # 现在，我们可以安全地导入并使用process_essay_correction提交任务
            from app.tasks.correction_tasks import process_essay_correction
            task_result = process_essay_correction.delay(essay_id)
            
            logger.info(f"测试作文已提交进入批改队列，任务ID: {task_result.id}")
            
            # 更新任务ID
            with db.session() as session:
                correction = session.query(Correction).filter_by(essay_id=essay_id).first()
                if correction:
                    correction.task_id = task_result.id
                    session.commit()
            
            return essay_id
            
        except Exception as e:
            logger.error(f"提交测试作文失败: {str(e)}")
            logger.exception(e)  # 打印详细堆栈信息
            return None

def monitor_essay_status(essay_id, max_attempts=30, interval=5):
    """监控作文批改状态"""
    # 在函数内部导入模块，避免潜在的循环引用问题
    from app import create_app
    from app.models.essay import Essay, EssayStatus
    from app.models.correction import Correction, CorrectionStatus
    
    app = create_app()
    with app.app_context():
        from app.models.db import db
        
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            
            try:
                with db.session() as session:
                    # 查询作文状态
                    essay = session.query(Essay).get(essay_id)
                    if not essay:
                        logger.error(f"找不到作文 ID={essay_id}")
                        return False
                    
                    # 查询批改状态
                    correction = session.query(Correction).filter_by(essay_id=essay_id).first()
                    
                    # 打印当前状态
                    logger.info(f"监控作文状态 (尝试 {attempt}/{max_attempts}):")
                    logger.info(f"  - 作文ID: {essay_id}")
                    logger.info(f"  - 作文状态: {essay.status}")
                    
                    if correction:
                        logger.info(f"  - 批改状态: {correction.status}")
                        logger.info(f"  - 任务ID: {correction.task_id}")
                        
                        # 如果有错误信息，显示错误
                        if correction.error:
                            logger.warning(f"  - 错误信息: {correction.error}")
                    else:
                        logger.warning("  - 未找到批改记录")
                    
                    # 检查是否完成
                    if essay.status == EssayStatus.COMPLETED:
                        logger.info(f"作文批改已完成，ID: {essay_id}")
                        return True
                    
                    # 检查是否失败
                    if essay.status == EssayStatus.FAILED:
                        logger.error(f"作文批改失败，ID: {essay_id}")
                        if correction and correction.error:
                            logger.error(f"错误原因: {correction.error}")
                        return False
                    
                    # 等待下一次检查
                    logger.info(f"等待 {interval} 秒后再次检查...")
                    time.sleep(interval)
                    
            except Exception as e:
                logger.error(f"监控作文状态时出错: {str(e)}")
                logger.exception(e)  # 打印详细堆栈信息
                time.sleep(interval)
        
        logger.warning(f"监控超时，未能在 {max_attempts * interval} 秒内完成批改")
        return False

def main():
    """主函数"""
    logger.info("开始测试作文批改功能...")
    
    # 提交测试作文
    essay_id = submit_test_essay()
    if not essay_id:
        logger.error("测试失败：无法提交作文")
        return
    
    # 监控批改状态
    success = monitor_essay_status(essay_id)
    
    if success:
        logger.info("测试成功：作文批改完成")
    else:
        logger.error("测试失败：作文批改未完成")

if __name__ == "__main__":
    main() 