"""
User Management Async Tasks Module
Handle asynchronous tasks related to user management
"""
import logging
import json
import time
from datetime import datetime
from celery import shared_task
from pathlib import Path
import sys

# Ensure working directory is correct
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.models.user import User
from app.models.db import db
from app.extensions import db as db_ext
from services.email_service import EmailService
from utils.websocket_manager import notify_user
# Import Flask application
from flask import current_app

# Get logger
logger = logging.getLogger(__name__)

@shared_task(name='tasks.user_tasks.send_welcome_email')
def send_welcome_email(user_id, email, username):
    """
    Send welcome email
    
    Args:
        user_id: User ID
        email: User email
        username: Username
    """
    try:
        email_service = EmailService()
        result = email_service.send_welcome_email(email, username)
        
        # Record email sending result
        logger.info(f"Welcome email sent, User ID: {user_id}, Result: {result}")
        return {"status": "success", "message": "Welcome email sent"}
    
    except Exception as e:
        logger.error(f"Failed to send welcome email, User ID: {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}

@shared_task(name='tasks.user_tasks.send_password_reset')
def send_password_reset(user_id, email, reset_token):
    """
    Send password reset email
    
    Args:
        user_id: User ID
        email: User email
        reset_token: Reset token
    """
    try:
        email_service = EmailService()
        result = email_service.send_password_reset_email(email, reset_token)
        
        # Record email sending result
        logger.info(f"Password reset email sent, User ID: {user_id}, Result: {result}")
        return {"status": "success", "message": "Password reset email sent"}
    
    except Exception as e:
        logger.error(f"Failed to send password reset email, User ID: {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}

@shared_task(name='tasks.user_tasks.reset_monthly_essay_count')
def reset_monthly_essay_count():
    """
    Reset users' monthly essay count limit
    Usually scheduled by Celery Beat, runs once per month
    """
    try:
        today = datetime.now()
        logger.info(f"Starting reset of user monthly essay counts. Current date: {today.strftime('%Y-%m-%d')}")
        
        # Find users that need to be reset
        with current_app.app_context():
            # Assuming User model has profile data or UserProfile is imported
            from app.models.user import UserProfile
            
            with db.session() as session:
                profiles = session.query(UserProfile).all()
                reset_count = 0
                
                for profile in profiles:
                    # Check if reset is needed
                    if profile.reset_date is None or \
                       (today - profile.reset_date).days >= 30:
                        
                        # Reset monthly usage
                        profile.essay_monthly_used = 0
                        profile.reset_date = today
                        reset_count += 1
                
                # Commit all changes
                if reset_count > 0:
                    session.commit()
                
        logger.info(f"Monthly essay count reset completed, total reset: {reset_count} users")
        return {
            "status": "success", 
            "reset_count": reset_count,
            "message": f"Reset {reset_count} users' monthly essay count limits"
        }
    
    except Exception as e:
        logger.error(f"Failed to reset monthly essay count: {str(e)}")
        return {"status": "error", "message": str(e)}

@shared_task(name='tasks.user_tasks.process_subscription')
def process_subscription(user_id, payment_id, plan_id, amount):
    """
    处理用户订阅
    
    Args:
        user_id: 用户ID
        payment_id: 支付ID
        plan_id: 订阅计划ID
        amount: 支付金额
    """
    try:
        from services.payment_service import PaymentService
        from app.models.user import UserProfile
        from app.models.membership import MembershipPlan
        
        logger.info(f"开始处理用户订阅, 用户ID: {user_id}, 支付ID: {payment_id}")
        
        # 验证支付状态
        payment_service = PaymentService()
        payment_status = payment_service.verify_payment(payment_id)
        
        if payment_status.get('status') != 'success':
            logger.warning(f"支付验证失败, 用户ID: {user_id}, 支付ID: {payment_id}")
            return {
                "status": "error",
                "message": "支付验证失败",
                "payment_status": payment_status
            }
        
        # 获取订阅计划详情
        with current_app.app_context():
            with db.session() as session:
                plan = session.query(MembershipPlan).get(plan_id)
                if not plan:
                    logger.error(f"订阅计划不存在, 计划ID: {plan_id}")
                    return {"status": "error", "message": "订阅计划不存在"}
                
                profile = session.query(UserProfile).filter_by(user_id=user_id).first()
                if not profile:
                    logger.error(f"用户资料不存在, 用户ID: {user_id}")
                    return {"status": "error", "message": "用户资料不存在"}
                
                # 计算新的过期时间
                from datetime import datetime, timedelta
                
                if profile.subscription_expires and profile.subscription_expires > datetime.now():
                    # 延长现有订阅
                    profile.subscription_expires += timedelta(days=plan.duration_days)
                else:
                    # 新订阅
                    profile.subscription_expires = datetime.now() + timedelta(days=plan.duration_days)
                
                # 更新订阅信息
                profile.subscription_status = 'active'
                profile.subscription_plan_id = plan.id
                profile.essay_monthly_limit = plan.max_essays_total
                profile.essay_monthly_used = 0
                
                # 创建订阅记录
                from app.models.subscription import Subscription
                subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    status='active',
                    start_date=datetime.now(),
                    end_date=profile.subscription_expires,
                    payment_method=payment_status.get('payment_method', 'unknown')
                )
                session.add(subscription)
                
                session.commit()
                
                # 发送订阅成功通知
                notify_user(user_id, {
                    "type": "subscription_updated",
                    "subscription": {
                        "expires": profile.subscription_expires.isoformat(),
                        "plan": plan.name,
                        "essay_limit": plan.max_essays_total
                    }
                })
                
                logger.info(f"用户订阅更新成功, 用户ID: {user_id}, 过期时间: {profile.subscription_expires}")
                
                return {
                    "status": "success",
                    "message": "订阅更新成功",
                    "subscription_expires": profile.subscription_expires.isoformat(),
                    "essay_limit": plan.max_essays_total
                }
    
    except Exception as e:
        logger.error(f"处理用户订阅失败, 用户ID: {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)} 
