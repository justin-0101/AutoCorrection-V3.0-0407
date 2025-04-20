#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文章批改任务模块
包含异步处理文章批改的任务函数
"""

import os
import time
import logging
import traceback
from flask import current_app
from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.core.correction.correction_service import CorrectionService
from app.extensions import db

logger = logging.getLogger(__name__)

@shared_task(bind=True, name='app.tasks.correction_tasks.process_essay_correction', queue='correction')
def process_essay_correction(self, essay_id):
    """
    处理文章批改任务
    
    Args:
        self: Celery任务实例
        essay_id: 文章ID
        
    Returns:
        dict: 包含批改结果的字典
    """
    # 导入一些必要的库，在函数内部导入避免循环导入
    import pytz
    from flask import has_app_context, current_app
    from app import create_app
    import traceback

    logger.info(f"开始处理文章批改任务，文章ID: {essay_id}")
    
    # 检查是否已在应用上下文中
    app = None
    ctx = None
    
    try:
        if not has_app_context():
            logger.info("未检测到应用上下文，正在创建新的应用上下文...")
            app = create_app()
            ctx = app.app_context()
            ctx.push()
            logger.info("已创建并推送新的应用上下文")
        else:
            logger.info("检测到现有应用上下文，继续使用当前上下文")
            app = current_app
        
        # 设置时区为Asia/Shanghai
        os.environ['TZ'] = 'Asia/Shanghai'
        try:
            import time
            time.tzset()  # 应用时区设置
            logger.info("已设置时区为Asia/Shanghai")
        except AttributeError:
            # Windows不支持tzset
            logger.warning("Windows环境不支持tzset，时区设置可能不生效")
        
        # 使用应用中已注册的db实例，而不是创建新的实例
        logger.info("测试数据库连接...")
        try:
            db.session.execute(text('SELECT 1'))
            logger.info("数据库连接测试成功")
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            raise
        
        # 查询文章并更新状态，使用事务确保原子性
        logger.info(f"查询文章 ID: {essay_id}")
        
        with db.session.begin():
            essay = db.session.get(Essay, essay_id)
            
            if not essay:
                logger.error(f"找不到文章 ID: {essay_id}")
                return {"success": False, "error": f"找不到文章 ID: {essay_id}"}
            
            # 更新文章状态为处理中
            logger.info(f"更新文章状态为处理中: {essay_id}")
            essay.status = EssayStatus.CORRECTING.value
            db.session.commit()
        
        # 初始化批改服务
        logger.info("初始化批改服务...")
        service = CorrectionService()
        
        # 执行批改
        logger.info(f"开始执行文章批改: {essay_id}")
        result = service.perform_correction(essay)
        
        # 检查批改结果
        if isinstance(result, dict) and 'status' in result:
            if result['status'] == 'success':
                logger.info(f"文章批改成功: {essay_id}, 得分: {result.get('score', 'N/A')}")
                # 批改成功，不需要额外更新状态，因为perform_correction已经更新了
                return {
                    "success": True, 
                    "result": result
                }
            else:
                # 批改失败，记录错误信息
                error_msg = result.get('message', '未知错误')
                logger.error(f"文章批改失败: {essay_id}, 错误: {error_msg}")
                # 检查状态并更新
                try:
                    with db.session.begin():
                        # 重新获取最新状态
                        essay = db.session.get(Essay, essay_id)
                        if essay and essay.status != EssayStatus.FAILED.value:
                            essay.status = EssayStatus.FAILED.value
                            essay.error_message = error_msg
                            db.session.commit()
                            logger.info(f"已更新文章状态为失败: {essay_id}")
                except Exception as update_err:
                    logger.error(f"更新文章错误状态失败: {str(update_err)}")
                    logger.error(traceback.format_exc())
                
                return {
                    "success": False, 
                    "error": error_msg
                }
        elif result is True:  
            # 兼容旧版API返回True表示成功
            logger.info(f"文章批改成功(旧版API): {essay_id}")
            return {"success": True}
        elif result is False:
            # 兼容旧版API返回False表示失败
            logger.error(f"文章批改失败(旧版API): {essay_id}")
            try:
                with db.session.begin():
                    essay = db.session.get(Essay, essay_id)
                    if essay and essay.status != EssayStatus.FAILED.value:
                        essay.status = EssayStatus.FAILED.value
                        essay.error_message = "批改服务返回失败"
                        db.session.commit()
            except Exception as e:
                logger.error(f"更新文章状态失败: {str(e)}")
            return {"success": False, "error": "批改失败"}
        else:
            # 未知返回类型
            logger.error(f"文章批改返回未知类型: {essay_id}, 类型: {type(result)}, 值: {result}")
            try:
                with db.session.begin():
                    essay = db.session.get(Essay, essay_id)
                    if essay and essay.status != EssayStatus.FAILED.value:
                        essay.status = EssayStatus.FAILED.value
                        essay.error_message = f"批改服务返回未知类型: {type(result)}"
                        db.session.commit()
            except Exception as e:
                logger.error(f"更新文章状态失败: {str(e)}")
            return {"success": False, "error": f"批改服务返回未知类型: {type(result)}"}
        
    except SQLAlchemyError as e:
        error_msg = f"数据库错误: {str(e)}"
        logger.error(f"批改文章时数据库错误: {error_msg}")
        logger.error(traceback.format_exc())
        
        # 尝试标记文章为错误状态
        try:
            with db.session.begin():
                essay = db.session.get(Essay, essay_id)
                if essay:
                    essay.status = EssayStatus.FAILED.value
                    essay.error_message = error_msg
                    db.session.commit()
        except Exception as ex:
            logger.error(f"无法更新文章错误状态: {str(ex)}")
            logger.error(traceback.format_exc())
            
        return {"success": False, "error": error_msg}
        
    except Exception as e:
        error_msg = f"处理文章批改时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # 尝试标记文章为错误状态
        try:
            with db.session.begin():
                essay = db.session.get(Essay, essay_id)
                if essay:
                    essay.status = EssayStatus.FAILED.value
                    essay.error_message = str(e)
                    db.session.commit()
        except Exception as ex:
            logger.error(f"无法更新文章错误状态: {str(ex)}")
            logger.error(traceback.format_exc())
            
        return {"success": False, "error": error_msg}
        
    finally:
        logger.info(f"文章批改任务处理完毕: {essay_id}")
        
        # 如果我们创建了应用上下文，确保弹出它
        if ctx:
            try:
                ctx.pop()
                logger.info("应用上下文已弹出")
            except Exception as ex:
                logger.warning(f"弹出应用上下文时出错: {str(ex)}")
                logger.warning(traceback.format_exc())