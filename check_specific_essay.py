import sys
import os
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 导入必要的模块
from app import create_app
from app.extensions import db
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus

def check_specific_essay(essay_id=20):
    """检查特定ID的作文及其对应的批改记录"""
    app = create_app()
    with app.app_context():
        try:
            # 查询作文
            essay = db.session.query(Essay).filter(Essay.id == essay_id).first()
            if not essay:
                logger.info(f"未找到ID为{essay_id}的作文")
                return
            
            # 打印作文信息
            logger.info(f"作文ID: {essay.id}")
            logger.info(f"作文标题: {essay.title}")
            logger.info(f"作文内容:\n            {essay.content[:100]}...")  # 只打印前100个字符
            logger.info(f"作文状态: {essay.status}")
            logger.info(f"作文提交时间: {essay.created_at}")
            logger.info(f"作文任务ID: {essay.task_id}")
            
            # 查询对应的批改记录
            corrections = db.session.query(Correction).filter(Correction.essay_id == essay_id).all()
            logger.info(f"找到{len(corrections)}条批改记录")
            
            for i, correction in enumerate(corrections):
                logger.info(f"==== 批改记录 {i+1} ====")
                logger.info(f"批改ID: {correction.id}")
                logger.info(f"批改状态: {correction.status}")
                logger.info(f"批改任务ID: {correction.task_id}")
                logger.info(f"批改开始时间: {correction.created_at}")
                logger.info(f"批改结束时间: {correction.updated_at}")
                logger.info(f"批改结果: {'有结果' if correction.result else '无结果'}")
                
                # 检查批改结果是否为NULL
                if correction.result:
                    logger.info(f"批改分数: {correction.result.get('score', 'N/A')}")
                    logger.info(f"批改评语: {correction.result.get('comments', 'N/A')[:100]}...")  # 只打印前100个字符
                else:
                    logger.info("批改结果为空")
            
            # 检查状态是否一致
            if essay.status == str(EssayStatus.CORRECTING.value):
                if not corrections or not any(c.status == str(CorrectionStatus.CORRECTING.value) for c in corrections):
                    logger.warning("作文状态为CORRECTING，但是没有对应的CORRECTING状态的批改记录！")
            
        except SQLAlchemyError as e:
            logger.error(f"数据库错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")

if __name__ == "__main__":
    # 从命令行获取essay_id参数，如果未提供则使用默认值
    essay_id = 20
    if len(sys.argv) > 1:
        try:
            essay_id = int(sys.argv[1])
            logger.info(f"将检查ID为{essay_id}的作文")
        except ValueError:
            logger.error("提供的作文ID必须为整数")
            sys.exit(1)
    else:
        logger.info(f"未提供作文ID，将使用默认ID: {essay_id}")
    
    check_specific_essay(essay_id) 