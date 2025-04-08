#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户相关异步任务模块
处理用户通知、邮件发送等异步任务
"""

import logging
import time
from celery import shared_task

from app.tasks.celery_app import celery_app
from app.utils.email_sender import send_email
from app.utils.exceptions import EmailError
from app.models.db import db
from app.models.user import User
from app.models.user_activity import UserActivity
from app.utils.websocket_manager import notify_user

# 获取logger
logger = logging.getLogger(__name__)

@shared_task(
    name='app.tasks.user_tasks.send_notification_email',
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 30},
    # 邮件发送任务应该很快完成
    soft_time_limit=60,
    time_limit=120
)
def send_notification_email(self, user_id=None, email=None, subject="系统通知", content="", template=None, template_data=None):
    """
    发送通知邮件
    
    Args:
        self: Celery任务实例
        user_id: 用户ID(可选)
        email: 收件人邮箱(可选，如果提供user_id则从用户信息获取)
        subject: 邮件主题
        content: 邮件内容
        template: 模板名称(可选)
        template_data: 模板数据(可选)
    
    Returns:
        dict: 发送结果
    """
    start_time = time.time()
    
    try:
        # 如果没有提供email但提供了user_id，从用户信息获取邮箱
        if not email and user_id:
            with db.session() as session:
                user = session.query(User).get(user_id)
                if user and user.email:
                    email = user.email
                    logger.info(f"从用户信息获取邮箱: {email}")
                else:
                    logger.error(f"用户未设置邮箱或用户不存在，ID: {user_id}")
                    return {
                        "status": "error",
                        "message": "用户未设置邮箱或用户不存在"
                    }
        
        if not email:
            logger.error("未提供邮箱地址，无法发送邮件")
            return {
                "status": "error",
                "message": "未提供邮箱地址"
            }
        
        logger.info(f"开始发送邮件至 {email}，主题: {subject}")
        
        # 发送邮件
        send_result = send_email(
            recipients=[email],
            subject=subject,
            content=content,
            template=template,
            template_data=template_data
        )
        
        if send_result.get("status") != "success":
            logger.error(f"发送邮件失败: {send_result.get('message')}")
            raise Exception(f"发送邮件失败: {send_result.get('message')}")
        
        # 记录发送结果
        if user_id:
            try:
                with db.session() as session:
                    # 记录用户活动
                    activity = UserActivity(
                        user_id=user_id,
                        activity_type="email_sent",
                        activity_data={
                            "subject": subject,
                            "timestamp": time.time()
                        }
                    )
                    session.add(activity)
                    session.commit()
                    
                    logger.info(f"邮件发送记录已保存, 用户ID: {user_id}")
            except Exception as e:
                logger.error(f"记录邮件发送活动失败: {str(e)}")
        
        processing_time = time.time() - start_time
        logger.info(f"邮件发送完成，耗时: {processing_time:.2f}秒")
        
        return {
            "status": "success",
            "message": "邮件发送成功",
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"发送邮件异常: {str(e)}", exc_info=True)
        # 重试任务
        raise e

@shared_task(name='app.tasks.user_tasks.send_verification_code')
def send_verification_code(user_id, email, code, purpose="register", expiry_minutes=30):
    """
    发送验证码
    
    Args:
        user_id: 用户ID
        email: 收件人邮箱
        code: 验证码
        purpose: 用途(register/login/reset_password)
        expiry_minutes: 过期时间(分钟)
    
    Returns:
        dict: 发送结果
    """
    try:
        purpose_subjects = {
            "register": "注册验证码",
            "login": "登录验证码",
            "reset_password": "密码重置验证码"
        }
        
        subject = purpose_subjects.get(purpose, "验证码")
        
        # 获取用户名
        username = email
        with db.session() as session:
            user = session.query(User).get(user_id)
            if user:
                username = user.username
        
        # 构建邮件内容
        content = f"""尊敬的{username}：
        
您的验证码是: {code}

此验证码将在{expiry_minutes}分钟后失效，请勿将验证码泄露给他人。

如非本人操作，请忽略此邮件。

作文批改系统
"""
        
        # 发送邮件
        return send_notification_email.delay(
            user_id=user_id,
            email=email,
            subject=f"作文批改系统 - {subject}",
            content=content
        )
    
    except Exception as e:
        logger.error(f"发送验证码异常: {str(e)}")
        return {
            "status": "error",
            "message": f"发送验证码异常: {str(e)}"
        }

@shared_task(name='app.tasks.user_tasks.process_user_activity')
def process_user_activity(user_id, activity_type, activity_data=None):
    """
    处理用户活动
    
    Args:
        user_id: 用户ID
        activity_type: 活动类型
        activity_data: 活动数据
    
    Returns:
        dict: 处理结果
    """
    try:
        logger.info(f"处理用户活动, 用户ID: {user_id}, 类型: {activity_type}")
        
        if activity_data is None:
            activity_data = {}
        
        # 记录用户活动
        with db.session() as session:
            activity = UserActivity(
                user_id=user_id,
                activity_type=activity_type,
                activity_data=activity_data
            )
            session.add(activity)
            session.commit()
        
        # 根据活动类型处理不同的逻辑
        if activity_type == "login":
            # 登录活动可能需要更新用户的最后登录时间
            with db.session() as session:
                user = session.query(User).get(user_id)
                if user:
                    user.last_login_time = time.time()
                    user.login_count = (user.login_count or 0) + 1
                    session.commit()
        
        elif activity_type == "essay_submitted":
            # 可以处理作文提交后的用户数据更新
            with db.session() as session:
                user = session.query(User).get(user_id)
                if user:
                    user.essay_count = (user.essay_count or 0) + 1
                    session.commit()
        
        return {
            "status": "success",
            "message": "用户活动处理成功",
            "activity_id": activity.id if 'activity' in locals() else None
        }
    
    except Exception as e:
        logger.error(f"处理用户活动异常: {str(e)}")
        return {
            "status": "error",
            "message": f"处理用户活动异常: {str(e)}"
        }

@shared_task(name='app.tasks.user_tasks.cleanup_inactive_users')
def cleanup_inactive_users(days_inactive=180):
    """
    清理长期不活跃用户
    将长期不活跃用户标记为非活跃状态
    通常由Celery Beat定时调度，每月运行一次
    
    Args:
        days_inactive: 不活跃天数
    
    Returns:
        dict: 处理结果
    """
    try:
        import datetime
        
        # 计算不活跃时间阈值
        inactive_threshold = datetime.datetime.now() - datetime.timedelta(days=days_inactive)
        timestamp_threshold = inactive_threshold.timestamp()
        
        logger.info(f"开始清理不活跃用户，不活跃时间阈值: {inactive_threshold}")
        
        with db.session() as session:
            # 查找不活跃用户
            inactive_users = session.query(User).filter(
                User.is_active == True,
                User.last_login_time < timestamp_threshold
            ).all()
            
            if not inactive_users:
                logger.info("没有发现不活跃用户")
                return {
                    "status": "success",
                    "message": "没有发现不活跃用户",
                    "count": 0
                }
            
            # 标记为非活跃
            for user in inactive_users:
                user.is_active = False
                
                # 可选：发送邮件通知用户账号已被标记为非活跃
                if user.email:
                    send_notification_email.delay(
                        user_id=user.id,
                        email=user.email,
                        subject="账号状态通知",
                        content=f"尊敬的{user.username}，您的账号已被标记为非活跃状态，因为您已超过{days_inactive}天未登录系统。如需继续使用，请登录系统重新激活您的账号。"
                    )
            
            session.commit()
            
            logger.info(f"清理不活跃用户完成，共标记: {len(inactive_users)}个用户")
            
            return {
                "status": "success",
                "message": f"已标记{len(inactive_users)}个不活跃用户",
                "count": len(inactive_users)
            }
    
    except Exception as e:
        logger.error(f"清理不活跃用户异常: {str(e)}")
        return {
            "status": "error",
            "message": f"清理不活跃用户异常: {str(e)}"
        } 