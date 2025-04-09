#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文服务模块
处理作文的创建、更新、查询和批改相关功能
"""

import logging
import time
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.models.db import db
from app.models.essay import Essay, EssayStatus, EssaySourceType
from app.models.correction import Correction, CorrectionStatus
from app.core.essay.essay_validator import EssayValidator
from app.errors import ValidationError, ResourceNotFoundError, ProcessingError
from app.utils.file_handler import FileHandler
from app.tasks.correction_tasks import process_essay_correction, batch_process_essays

logger = logging.getLogger(__name__)

class EssayService:
    """作文服务类，处理作文相关的业务逻辑"""
    
    @classmethod
    def create_essay(cls, user_id, title, content, source_type=EssaySourceType.text.value,
                    grade=None, author_name=None, is_public=False):
        """
        创建新作文，在同一事务中创建作文和批改记录
        
        Args:
            user_id: 用户ID
            title: 作文标题
            content: 作文内容
            source_type: 来源类型
            grade: 年级水平
            author_name: 作者姓名
            is_public: 是否公开
        
        Returns:
            dict: 包含新创建的作文信息
        """
        try:
            # 验证作文数据
            EssayValidator.validate_essay_data(title=title, content=content)
            
            # 计算字数
            word_count = len(content)
            
            # 开始数据库事务
            with db.session.begin():
                # 创建新作文记录
                essay = Essay(
                    user_id=user_id,
                    title=title,
                    content=content,
                    word_count=word_count,
                    source_type=source_type,
                    grade=grade,
                    author_name=author_name,
                    is_public=is_public,
                    status=EssayStatus.PENDING.value,
                    created_at=datetime.utcnow()
                )
                
                # 添加到数据库
                db.session.add(essay)
                db.session.flush()  # 获取essay.id
                
                # 创建批改记录
                correction = Correction(
                    essay_id=essay.id,
                    status=CorrectionStatus.PENDING.value,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(correction)
                # 事务会在with块结束时自动提交
            
            logger.info(f"作文创建成功，ID: {essay.id}, 用户: {user_id}")
            
            # 异步启动作文批改任务
            correction_task = process_essay_correction.delay(essay.id)
            
            return {
                "status": "success",
                "message": "作文创建成功，已加入批改队列",
                "essay_id": essay.id,
                "task_id": correction_task.id
            }
        
        except ValidationError as e:
            logger.error(f"作文数据验证失败: {str(e)}")
            raise
        
        except SQLAlchemyError as e:
            logger.error(f"数据库操作失败: {str(e)}")
            raise ProcessingError(f"创建作文失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"创建作文异常: {str(e)}", exc_info=True)
            raise ProcessingError(f"创建作文失败: {str(e)}")
    
    @classmethod
    def create_essay_from_file(cls, user_id, file_data, filename, title=None, grade=None, author_name=None, is_public=False):
        """
        从上传的文件创建作文
        
        Args:
            user_id: 用户ID
            file_data: 文件数据
            filename: 文件名
            title: 作文标题(可选)
            grade: 年级水平(可选)
            author_name: 作者姓名(可选)
            is_public: 是否公开
        
        Returns:
            dict: 包含新创建的作文信息
        """
        try:
            # 处理文件
            file_handler = FileHandler()
            file_info = file_handler.process_file(file_data, filename)
            
            if not file_info:
                raise ValidationError("无法处理上传的文件")
            
            # 从文件中提取内容
            content = file_info.get('content', '')
            
            if not content:
                raise ValidationError("无法从文件中提取内容")
            
            # 如果未提供标题，使用文件名作为标题
            if not title:
                title = filename.split('.')[0]
            
            # 创建作文
            return cls.create_essay(
                user_id=user_id,
                title=title,
                content=content,
                source_type=EssaySourceType.upload.value,
                grade=grade,
                author_name=author_name,
                is_public=is_public
            )
        
        except ValidationError as e:
            logger.error(f"文件验证失败: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"从文件创建作文异常: {str(e)}", exc_info=True)
            raise ProcessingError(f"从文件创建作文失败: {str(e)}")
    
    @classmethod
    def get_essay(cls, essay_id, user_id=None):
        """
        获取作文详情
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID(用于验证权限)
        
        Returns:
            dict: 作文详情
        """
        try:
            with db.session() as session:
                essay = session.query(Essay).get(essay_id)
                
                if not essay:
                    raise ResourceNotFoundError(f"找不到ID为{essay_id}的作文")
                
                # 如果指定了用户ID，验证权限
                if user_id and essay.user_id != user_id:
                    # 检查用户是否为管理员
                    user = session.query(User).get(user_id)
                    if not user or not user.is_admin:
                        raise ValidationError("您没有权限查看此作文")
                
                # 转换为字典
                essay_data = {
                    "id": essay.id,
                    "user_id": essay.user_id,
                    "title": essay.title,
                    "content": essay.content,
                    "grade_level": essay.grade_level,
                    "essay_type": essay.essay_type,
                    "requirements": essay.requirements,
                    "word_count": essay.word_count,
                    "status": essay.status,
                    "score": essay.score,
                    "correction_data": essay.correction_data,
                    "created_at": essay.created_at,
                    "updated_at": essay.updated_at,
                    "completion_time": essay.completion_time,
                    "source_file": essay.source_file,
                    "source_type": essay.source_type
                }
                
                return {
                    "status": "success",
                    "essay": essay_data
                }
        
        except ResourceNotFoundError as e:
            logger.error(str(e))
            raise e
        
        except ValidationError as e:
            logger.error(str(e))
            raise e
        
        except Exception as e:
            logger.error(f"获取作文异常: {str(e)}", exc_info=True)
            raise ProcessingError(f"获取作文失败: {str(e)}")
    
    @classmethod
    def get_user_essays(cls, user_id, status=None, page=1, per_page=10):
        """
        获取用户的作文列表
        
        Args:
            user_id: 用户ID
            status: 作文状态筛选(可选)
            page: 页码
            per_page: 每页数量
        
        Returns:
            dict: 包含作文列表的结果
        """
        try:
            with db.session() as session:
                # 构建查询
                query = session.query(Essay).filter(Essay.user_id == user_id)
                
                # 应用状态筛选
                if status:
                    query = query.filter(Essay.status == status)
                
                # 获取总数
                total_count = query.count()
                
                # 分页
                essays = query.order_by(Essay.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
                
                # 转换为列表
                essay_list = []
                for essay in essays:
                    essay_list.append({
                        "id": essay.id,
                        "title": essay.title,
                        "grade_level": essay.grade_level,
                        "essay_type": essay.essay_type,
                        "word_count": essay.word_count,
                        "status": essay.status,
                        "score": essay.score,
                        "created_at": essay.created_at,
                        "completion_time": essay.completion_time,
                        "source_type": essay.source_type
                    })
                
                return {
                    "status": "success",
                    "essays": essay_list,
                    "pagination": {
                        "total": total_count,
                        "page": page,
                        "per_page": per_page,
                        "pages": (total_count + per_page - 1) // per_page
                    }
                }
        
        except Exception as e:
            logger.error(f"获取用户作文列表异常，用户ID: {user_id}: {str(e)}", exc_info=True)
            raise ProcessingError(f"获取用户作文列表失败: {str(e)}")
    
    @classmethod
    def update_essay(cls, essay_id, user_id, data):
        """
        更新作文信息
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID
            data: 要更新的作文数据
        
        Returns:
            dict: 更新结果
        """
        try:
            with db.session() as session:
                essay = session.query(Essay).get(essay_id)
                
                if not essay:
                    raise ResourceNotFoundError(f"找不到ID为{essay_id}的作文")
                
                # 验证权限
                if essay.user_id != user_id:
                    # 检查用户是否为管理员
                    user = session.query(User).get(user_id)
                    if not user or not user.is_admin:
                        raise ValidationError("您没有权限更新此作文")
                
                # 验证状态
                if essay.status not in ['pending', 'failed']:
                    raise ValidationError(f"当前状态({essay.status})的作文不能被更新")
                
                # 更新字段
                allowed_fields = ['title', 'content', 'grade_level', 'essay_type', 'requirements']
                updated = False
                
                for field in allowed_fields:
                    if field in data and data[field] is not None:
                        setattr(essay, field, data[field])
                        updated = True
                
                # 如果内容更新了，重新计算字数
                if 'content' in data and data['content'] is not None:
                    essay.word_count = len(data['content'])
                
                if updated:
                    # 更新状态为待处理
                    essay.status = 'pending'
                    essay.updated_at = time.time()
                    essay.completion_time = None
                    essay.score = None
                    essay.correction_data = None
                    essay.failure_reason = None
                    
                    session.commit()
                    
                    # 重新启动作文批改任务
                    correction_task = process_essay_correction.delay(essay_id, user_id)
                    
                    logger.info(f"作文更新成功，ID: {essay_id}, 用户: {user_id}, 已重新加入批改队列")
                    
                    return {
                        "status": "success",
                        "message": "作文更新成功，已重新加入批改队列",
                        "essay_id": essay_id,
                        "task_id": correction_task.id
                    }
                else:
                    return {
                        "status": "success",
                        "message": "作文无变化，未进行更新",
                        "essay_id": essay_id
                    }
        
        except ResourceNotFoundError as e:
            logger.error(str(e))
            raise e
        
        except ValidationError as e:
            logger.error(str(e))
            raise e
        
        except Exception as e:
            logger.error(f"更新作文异常，ID: {essay_id}: {str(e)}", exc_info=True)
            raise ProcessingError(f"更新作文失败: {str(e)}")
    
    @classmethod
    def delete_essay(cls, essay_id, user_id):
        """
        删除作文
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID
        
        Returns:
            dict: 删除结果
        """
        try:
            with db.session() as session:
                essay = session.query(Essay).get(essay_id)
                
                if not essay:
                    raise ResourceNotFoundError(f"找不到ID为{essay_id}的作文")
                
                # 验证权限
                if essay.user_id != user_id:
                    # 检查用户是否为管理员
                    user = session.query(User).get(user_id)
                    if not user or not user.is_admin:
                        raise ValidationError("您没有权限删除此作文")
                
                session.delete(essay)
                session.commit()
                
                logger.info(f"作文删除成功，ID: {essay_id}, 用户: {user_id}")
                
                return {
                    "status": "success",
                    "message": "作文删除成功",
                    "essay_id": essay_id
                }
        
        except ResourceNotFoundError as e:
            logger.error(str(e))
            raise e
        
        except ValidationError as e:
            logger.error(str(e))
            raise e
        
        except Exception as e:
            logger.error(f"删除作文异常，ID: {essay_id}: {str(e)}", exc_info=True)
            raise ProcessingError(f"删除作文失败: {str(e)}")
    
    @classmethod
    def retry_correction(cls, essay_id, user_id):
        """
        重试作文批改
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID
        
        Returns:
            dict: 重试结果
        """
        try:
            with db.session() as session:
                essay = session.query(Essay).get(essay_id)
                
                if not essay:
                    raise ResourceNotFoundError(f"找不到ID为{essay_id}的作文")
                
                # 验证权限
                if essay.user_id != user_id:
                    # 检查用户是否为管理员
                    user = session.query(User).get(user_id)
                    if not user or not user.is_admin:
                        raise ValidationError("您没有权限重试此作文的批改")
                
                # 验证状态
                if essay.status not in ['failed', 'pending']:
                    raise ValidationError(f"当前状态({essay.status})的作文不需要重新批改")
                
                # 更新状态
                essay.status = 'pending'
                essay.failure_reason = None
                essay.updated_at = time.time()
                
                session.commit()
                
                # 重新启动作文批改任务
                correction_task = process_essay_correction.delay(essay_id, user_id)
                
                logger.info(f"作文批改重试，ID: {essay_id}, 用户: {user_id}")
                
                return {
                    "status": "success",
                    "message": "作文已重新加入批改队列",
                    "essay_id": essay_id,
                    "task_id": correction_task.id
                }
        
        except ResourceNotFoundError as e:
            logger.error(str(e))
            raise e
        
        except ValidationError as e:
            logger.error(str(e))
            raise e
        
        except Exception as e:
            logger.error(f"重试作文批改异常，ID: {essay_id}: {str(e)}", exc_info=True)
            raise ProcessingError(f"重试作文批改失败: {str(e)}")
    
    @classmethod
    def batch_submit_essays(cls, user_id, essays_data):
        """
        批量提交作文
        
        Args:
            user_id: 用户ID
            essays_data: 作文数据列表
        
        Returns:
            dict: 批量提交结果
        """
        try:
            if not essays_data or not isinstance(essays_data, list):
                raise ValidationError("无效的作文数据列表")
            
            essay_ids = []
            
            for essay_data in essays_data:
                # 验证作文数据
                title = essay_data.get('title')
                content = essay_data.get('content')
                grade_level = essay_data.get('grade_level')
                essay_type = essay_data.get('essay_type')
                requirements = essay_data.get('requirements')
                
                EssayValidator.validate_essay_data(title, content, grade_level, essay_type)
                
                # 创建新作文记录
                essay = Essay(
                    user_id=user_id,
                    title=title,
                    content=content,
                    grade_level=grade_level,
                    essay_type=essay_type,
                    requirements=requirements,
                    word_count=len(content),
                    status='pending',
                    created_at=time.time()
                )
                
                with db.session() as session:
                    session.add(essay)
                    session.commit()
                    essay_ids.append(essay.id)
            
            logger.info(f"批量作文提交成功，数量: {len(essay_ids)}, 用户: {user_id}")
            
            # 启动批量批改任务
            batch_task = batch_process_essays.delay(essay_ids)
            
            return {
                "status": "success",
                "message": f"已成功提交{len(essay_ids)}篇作文，批改任务已启动",
                "essay_ids": essay_ids,
                "task_id": batch_task.id
            }
        
        except ValidationError as e:
            logger.error(f"批量作文数据验证失败: {str(e)}")
            raise e
        
        except Exception as e:
            logger.error(f"批量提交作文异常: {str(e)}", exc_info=True)
            raise ProcessingError(f"批量提交作文失败: {str(e)}")
    
    @classmethod
    def get_correction_status(cls, essay_id, user_id=None):
        """
        获取作文批改状态
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID(用于验证权限)
        
        Returns:
            dict: 批改状态
        """
        try:
            with db.session() as session:
                essay = session.query(Essay).get(essay_id)
                
                if not essay:
                    raise ResourceNotFoundError(f"找不到ID为{essay_id}的作文")
                
                # 如果指定了用户ID，验证权限
                if user_id and essay.user_id != user_id:
                    # 检查用户是否为管理员
                    user = session.query(User).get(user_id)
                    if not user or not user.is_admin:
                        raise ValidationError("您没有权限查看此作文的批改状态")
                
                # 获取状态信息
                status_info = {
                    "essay_id": essay.id,
                    "status": essay.status,
                    "created_at": essay.created_at,
                    "updated_at": essay.updated_at
                }
                
                if essay.status == 'completed':
                    status_info.update({
                        "score": essay.score,
                        "completion_time": essay.completion_time,
                        "processing_time": essay.completion_time - essay.created_at if essay.completion_time else None
                    })
                elif essay.status == 'failed':
                    status_info.update({
                        "failure_reason": essay.failure_reason
                    })
                
                return {
                    "status": "success",
                    "correction_status": status_info
                }
        
        except ResourceNotFoundError as e:
            logger.error(str(e))
            raise e
        
        except ValidationError as e:
            logger.error(str(e))
            raise e
        
        except Exception as e:
            logger.error(f"获取批改状态异常，ID: {essay_id}: {str(e)}", exc_info=True)
            raise ProcessingError(f"获取批改状态失败: {str(e)}") 