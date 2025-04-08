#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知服务模块
处理系统内部通知、邮件通知和推送通知
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.config import config
from app.models.user import User
from app.models.notification import Notification, NotificationType
from app.models.db import db
from app.utils.websocket_manager import notify_user
from app.utils.email_sender import send_email
from app.utils.exceptions import EmailError

logger = logging.getLogger(__name__)

class NotificationService:
    """通知服务类，处理系统通知、邮件和推送"""
    
    def __init__(self):
        """初始化通知服务"""
        self.email_config = config.MAIL_CONFIG
    
    def send_notification(self, user_id: int, title: str, content: str, 
                           notification_type: str, context_data: dict = None) -> Dict[str, Any]:
        """
        发送系统通知
        
        Args:
            user_id: 接收用户ID
            title: 通知标题
            content: 通知内容
            notification_type: 通知类型
            context_data: 上下文数据
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 检查用户
            user = db.session.query(User).filter_by(id=user_id).first()
            if not user:
                logger.warning(f"发送通知失败: 用户不存在 ID={user_id}")
                return {
                    "status": "error",
                    "message": "用户不存在"
                }
            
            # 创建通知记录
            notification = Notification(
                user_id=user_id,
                title=title,
                content=content,
                notification_type=notification_type,
                context_data=json.dumps(context_data) if context_data else None
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # 尝试发送WebSocket实时通知
            try:
                notify_user(user_id, "notification", {
                    "id": notification.id,
                    "title": title,
                    "type": notification_type
                })
            except Exception as ws_error:
                logger.warning(f"WebSocket通知发送失败: {str(ws_error)}")
                # WebSocket通知失败不影响通知创建
            
            return {
                "status": "success",
                "notification_id": notification.id,
                "message": "通知已发送"
            }
        
        except Exception as e:
            logger.error(f"发送通知时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_notifications(self, user_id: int, page: int = 1, 
                          per_page: int = 20, only_unread: bool = False) -> Dict[str, Any]:
        """
        获取用户通知列表
        
        Args:
            user_id: 用户ID
            page: 页码
            per_page: 每页数量
            only_unread: 是否只获取未读通知
            
        Returns:
            Dict: 通知列表
        """
        try:
            # 检查用户
            user = db.session.query(User).filter_by(id=user_id).first()
            if not user:
                logger.warning(f"获取通知失败: 用户不存在 ID={user_id}")
                return {
                    "status": "error",
                    "message": "用户不存在"
                }
            
            # 构建查询
            query = db.session.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_deleted == False
            )
            
            if only_unread:
                query = query.filter(Notification.is_read == False)
            
            # 计算总数
            total = query.count()
            
            # 分页
            notifications = query.order_by(Notification.created_at.desc())\
                .offset((page - 1) * per_page).limit(per_page).all()
            
            # 格式化返回结果
            result = {
                "status": "success",
                "total": total,
                "page": page,
                "per_page": per_page,
                "notifications": [notification.to_dict() for notification in notifications]
            }
            
            return result
        
        except Exception as e:
            logger.error(f"获取通知列表时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
    
    def mark_as_read(self, notification_id: int, user_id: int) -> Dict[str, Any]:
        """
        标记通知为已读
        
        Args:
            notification_id: 通知ID
            user_id: 用户ID (用于验证权限)
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 查找通知
            notification = db.session.query(Notification).filter_by(id=notification_id).first()
            
            if not notification:
                return {
                    "status": "error",
                    "message": "通知不存在"
                }
            
            # 验证权限
            if notification.user_id != user_id:
                return {
                    "status": "error",
                    "message": "无权操作此通知"
                }
            
            # 标记为已读
            notification.mark_as_read()
            db.session.commit()
            
            return {
                "status": "success",
                "message": "通知已标记为已读"
            }
        
        except Exception as e:
            logger.error(f"标记通知已读时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def mark_all_as_read(self, user_id: int) -> Dict[str, Any]:
        """
        标记所有通知为已读
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 查找用户所有未读通知
            unread_notifications = db.session.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_deleted == False
            ).all()
            
            count = len(unread_notifications)
            
            # 标记所有为已读
            for notification in unread_notifications:
                notification.mark_as_read()
            
            db.session.commit()
            
            return {
                "status": "success",
                "message": f"{count} 条通知已标记为已读"
            }
        
        except Exception as e:
            logger.error(f"标记所有通知已读时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def delete_notification(self, notification_id: int, user_id: int) -> Dict[str, Any]:
        """
        删除通知 (逻辑删除)
        
        Args:
            notification_id: 通知ID
            user_id: 用户ID (用于验证权限)
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 查找通知
            notification = db.session.query(Notification).filter_by(id=notification_id).first()
            
            if not notification:
                return {
                    "status": "error",
                    "message": "通知不存在"
                }
            
            # 验证权限
            if notification.user_id != user_id:
                return {
                    "status": "error",
                    "message": "无权操作此通知"
                }
            
            # 逻辑删除
            notification.delete()
            db.session.commit()
            
            return {
                "status": "success",
                "message": "通知已删除"
            }
        
        except Exception as e:
            logger.error(f"删除通知时发生错误: {str(e)}", exc_info=True)
            db.session.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def send_email_notification(self, email: str, subject: str, 
                                 body: str, is_html: bool = False) -> Dict[str, Any]:
        """
        发送邮件通知
        
        Args:
            email: 接收者邮箱
            subject: 邮件主题
            body: 邮件内容
            is_html: 是否为HTML格式
            
        Returns:
            Dict: 处理结果
        """
        try:
            result = send_email(recipient=email, subject=subject, 
                                body=body, is_html=is_html)
            
            if result.get("status") == "success":
                return {
                    "status": "success",
                    "message": "邮件已发送"
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("message")
                }
        
        except EmailError as e:
            logger.error(f"发送邮件通知时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"发送邮件通知时发生未知错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"发送邮件失败: {str(e)}"
            }
    
    def send_subscription_expiring_notification(self, user_id: int, email: str, username: str,
                                             subscription_id: int, plan_name: str, 
                                             expire_date: str, days_left: int) -> Dict[str, Any]:
        """
        发送会员即将过期通知
        
        Args:
            user_id: 用户ID
            email: 用户邮箱
            username: 用户名
            subscription_id: 订阅ID
            plan_name: 会员计划名称
            expire_date: 过期日期
            days_left: 剩余天数
            
        Returns:
            Dict: 操作结果
        """
        try:
            # 创建系统通知
            notification_title = f"您的{plan_name}即将到期"
            notification_content = f"您的{plan_name}将于{expire_date}到期，还有{days_left}天。为了不影响您的使用，请及时续费。"
            
            self.send_notification(
                user_id=user_id,
                title=notification_title,
                content=notification_content,
                notification_type="subscription",
                context_data={
                    "subscription_id": subscription_id,
                    "plan_name": plan_name,
                    "expire_date": expire_date,
                    "days_left": days_left,
                    "renewal_url": f"https://yourdomain.com/membership/renew/{subscription_id}"
                }
            )
            
            # 发送邮件通知
            subject = f"【作文批改系统】您的{plan_name}即将到期"
            template = "subscription_expiring"
            template_data = {
                "username": username,
                "plan_name": plan_name,
                "expire_date": expire_date,
                "days_left": days_left,
                "renewal_url": f"https://yourdomain.com/membership/renew/{subscription_id}"
            }
            
            email_result = self.send_email_notification(
                email=email,
                subject=subject,
                body=template,
                is_html=True
            )
            
            if email_result.get("status") != "success":
                logger.warning(f"订阅到期邮件发送失败: {email_result.get('message')}")
            
            return {
                "status": "success",
                "message": "会员到期通知已发送"
            }
            
        except Exception as e:
            logger.error(f"发送会员到期通知失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"发送会员到期通知失败: {str(e)}"
            }
    
    def send_payment_success_notification(self, user_id: int, email: str, username: str,
                                       payment_id: int, amount: float, plan_name: str,
                                       subscription_end_date: str) -> Dict[str, Any]:
        """
        发送支付成功通知
        
        Args:
            user_id: 用户ID
            email: 用户邮箱
            username: 用户名
            payment_id: 支付ID
            amount: 支付金额
            plan_name: 会员计划名称
            subscription_end_date: 订阅结束日期
            
        Returns:
            Dict: 操作结果
        """
        try:
            # 创建系统通知
            notification_title = "支付成功通知"
            notification_content = f"您已成功支付{amount}元，{plan_name}已激活，有效期至{subscription_end_date}。"
            
            self.send_notification(
                user_id=user_id,
                title=notification_title,
                content=notification_content,
                notification_type="payment",
                context_data={
                    "payment_id": payment_id,
                    "amount": amount,
                    "plan_name": plan_name,
                    "subscription_end_date": subscription_end_date
                }
            )
            
            # 发送邮件通知
            subject = "【作文批改系统】支付成功通知"
            template = "payment_success"
            template_data = {
                "username": username,
                "plan_name": plan_name,
                "amount": amount,
                "subscription_end_date": subscription_end_date,
                "payment_id": payment_id
            }
            
            email_result = self.send_email_notification(
                email=email,
                subject=subject,
                body=template,
                is_html=True
            )
            
            if email_result.get("status") != "success":
                logger.warning(f"支付成功邮件发送失败: {email_result.get('message')}")
            
            return {
                "status": "success",
                "message": "支付成功通知已发送"
            }
            
        except Exception as e:
            logger.error(f"发送支付成功通知失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"发送支付成功通知失败: {str(e)}"
            }
    
    def send_subscription_expired_notification(self, user_id: int, email: str, username: str,
                                            plan_name: str) -> Dict[str, Any]:
        """
        发送会员已过期通知
        
        Args:
            user_id: 用户ID
            email: 用户邮箱
            username: 用户名
            plan_name: 会员计划名称
            
        Returns:
            Dict: 操作结果
        """
        try:
            # 创建系统通知
            notification_title = f"您的{plan_name}已过期"
            notification_content = f"您的{plan_name}已过期，部分功能将受到限制。为了继续享受完整功能，请重新订阅。"
            
            self.send_notification(
                user_id=user_id,
                title=notification_title,
                content=notification_content,
                notification_type="subscription"
            )
            
            # 发送邮件通知
            subject = f"【作文批改系统】您的{plan_name}已过期"
            template = "subscription_expired"
            template_data = {
                "username": username,
                "plan_name": plan_name,
                "renewal_url": "https://yourdomain.com/membership"
            }
            
            email_result = self.send_email_notification(
                email=email,
                subject=subject,
                body=template,
                is_html=True
            )
            
            if email_result.get("status") != "success":
                logger.warning(f"会员过期邮件发送失败: {email_result.get('message')}")
            
            return {
                "status": "success",
                "message": "会员过期通知已发送"
            }
            
        except Exception as e:
            logger.error(f"发送会员过期通知失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"发送会员过期通知失败: {str(e)}"
            } 