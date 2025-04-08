#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
管理员服务模块
提供管理后台所需的用户管理、数据统计和系统配置功能
"""

import logging
from datetime import datetime, timedelta
import json

from app.database.models import db, User, Essay, Subscription, Payment, UserProfile, Membership, MembershipPlan, Role
from app.utils.exceptions import ValidationError, ResourceNotFoundError

# 获取logger
logger = logging.getLogger(__name__)

class AdminService:
    """管理员服务类"""
    
    def __init__(self):
        """初始化管理员服务"""
        pass
    
    def get_users(self, page=1, per_page=10, username=None, email=None, role=None, is_active=None):
        """
        获取用户列表
        
        Args:
            page: 页码
            per_page: 每页数量
            username: 用户名过滤
            email: 邮箱过滤
            role: 角色过滤
            is_active: 是否激活过滤
            
        Returns:
            dict: 用户列表分页数据
        """
        try:
            query = User.query
            
            # 应用过滤条件
            if username:
                query = query.filter(User.username.like(f'%{username}%'))
            if email:
                query = query.filter(User.email.like(f'%{email}%'))
            if role:
                query = query.filter(User.role == role)
            if is_active is not None:
                query = query.filter(User.is_active == is_active)
            
            # 分页
            pagination = query.order_by(User.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 格式化响应
            users = []
            for user in pagination.items:
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                }
                users.append(user_data)
            
            return {
                "status": "success",
                "data": {
                    "users": users,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "current_page": page,
                    "per_page": per_page
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取用户列表失败: {str(e)}"
            }
    
    def get_user_detail(self, user_id):
        """
        获取用户详情
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 用户详情
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return {
                    "status": "error",
                    "message": f"用户不存在: {user_id}"
                }
            
            # 获取用户资料
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            
            # 获取用户订阅
            subscriptions = Subscription.query.filter_by(user_id=user_id).order_by(Subscription.created_at.desc()).all()
            
            # 获取用户批改的作文
            essays = Essay.query.filter_by(user_id=user_id).order_by(Essay.created_at.desc()).limit(10).all()
            
            # 格式化响应
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "profile": {
                    "essay_monthly_limit": profile.essay_monthly_limit if profile else None,
                    "essay_monthly_used": profile.essay_monthly_used if profile else None,
                    "subscription_expires": profile.subscription_expires.isoformat() if profile and profile.subscription_expires else None,
                    "daily_reset_date": profile.reset_date.isoformat() if profile and profile.reset_date else None
                },
                "subscriptions": [
                    {
                        "id": sub.id,
                        "plan": sub.plan,
                        "start_date": sub.start_date.isoformat() if sub.start_date else None,
                        "end_date": sub.end_date.isoformat() if sub.end_date else None,
                        "is_active": sub.is_active
                    } for sub in subscriptions
                ],
                "essays": [
                    {
                        "id": essay.id,
                        "title": essay.title,
                        "created_at": essay.created_at.isoformat() if essay.created_at else None,
                        "status": essay.status,
                        "word_count": essay.word_count
                    } for essay in essays
                ]
            }
            
            return {
                "status": "success",
                "data": user_data
            }
            
        except Exception as e:
            logger.error(f"获取用户详情失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取用户详情失败: {str(e)}"
            }
    
    def update_user(self, user_id, data):
        """
        更新用户信息 (包括角色)
        
        Args:
            user_id: 用户ID
            data: 用户数据, 可能包含 name, email, is_active, role_names (list of role names)
            
        Returns:
            dict: 操作结果
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return {"status": "error", "message": f"用户不存在: {user_id}"}

            updated = False
            # 更新基本信息 (除角色外)
            allowed_fields = ["name", "email", "is_active"]
            for field in allowed_fields:
                if field in data:
                    # Add validation if necessary, e.g., for email format or uniqueness if changed
                    if field == 'email' and data['email'] != user.email:
                        existing_user = User.query.filter(User.email == data['email'], User.id != user_id).first()
                        if existing_user:
                            return {"status": "error", "message": f"邮箱 {data['email']} 已被其他用户使用"}
                    setattr(user, field, data[field])
                    updated = True
                    logger.info(f"用户 {user_id} 的 {field} 已更新")

            # 更新角色
            if 'role_names' in data and isinstance(data['role_names'], list):
                target_role_names = set(data['role_names'])
                current_role_names = {role.name for role in user.roles}

                # 找出需要添加的角色
                roles_to_add_names = target_role_names - current_role_names
                if roles_to_add_names:
                    roles_to_add = Role.query.filter(Role.name.in_(roles_to_add_names)).all()
                    if len(roles_to_add) != len(roles_to_add_names):
                        # Some requested roles don't exist
                        found_names = {r.name for r in roles_to_add}
                        missing_names = roles_to_add_names - found_names
                        logger.warning(f"尝试为用户 {user_id} 添加不存在的角色: {missing_names}")
                        # Decide whether to proceed with found roles or return error
                        # For now, proceed with found roles
                    for role in roles_to_add:
                        user.add_role(role) # Use the existing helper method
                        updated = True
                        logger.info(f"为用户 {user_id} 添加了角色: {role.name}")

                # 找出需要移除的角色
                roles_to_remove_names = current_role_names - target_role_names
                if roles_to_remove_names:
                    roles_to_remove = Role.query.filter(Role.name.in_(roles_to_remove_names)).all()
                    for role in roles_to_remove:
                        user.remove_role(role) # Use the existing helper method
                        updated = True
                        logger.info(f"为用户 {user_id} 移除了角色: {role.name}")
            
            if updated:
                db.session.commit()
                logger.info(f"管理员成功更新了用户信息: {user_id}")
                return {"status": "success", "message": "用户信息已更新"}
            else:
                 return {"status": "success", "message": "未提供有效更新或信息无变化"}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新用户信息失败 (用户ID: {user_id}): {str(e)}", exc_info=True)
            return {"status": "error", "message": f"更新用户信息失败: {str(e)}"}
    
    def reset_user_password(self, user_id, new_password):
        """
        重置用户密码
        
        Args:
            user_id: 用户ID
            new_password: 新密码
            
        Returns:
            dict: 操作结果
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return {
                    "status": "error",
                    "message": f"用户不存在: {user_id}"
                }
            
            user.set_password(new_password)
            db.session.commit()
            
            logger.info(f"管理员重置了用户密码: {user_id}")
            return {
                "status": "success",
                "message": "用户密码已重置"
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"重置用户密码失败: {str(e)}")
            return {
                "status": "error",
                "message": f"重置用户密码失败: {str(e)}"
            }
    
    def get_essays(self, page=1, per_page=10, title=None, status=None, user_id=None, start_date=None, end_date=None):
        """
        获取作文列表
        
        Args:
            page: 页码
            per_page: 每页数量
            title: 标题过滤
            status: 状态过滤
            user_id: 用户ID过滤
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 作文列表分页数据
        """
        try:
            query = Essay.query
            
            # 应用过滤条件
            if title:
                query = query.filter(Essay.title.like(f'%{title}%'))
            if status:
                query = query.filter(Essay.status == status)
            if user_id:
                query = query.filter(Essay.user_id == user_id)
            
            # 日期过滤
            if start_date:
                start = datetime.fromisoformat(start_date)
                query = query.filter(Essay.created_at >= start)
            if end_date:
                end = datetime.fromisoformat(end_date)
                end = end + timedelta(days=1)  # 包含结束日期
                query = query.filter(Essay.created_at < end)
            
            # 分页
            pagination = query.order_by(Essay.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # 格式化响应
            essays = []
            for essay in pagination.items:
                # 获取用户信息
                user = User.query.get(essay.user_id)
                
                essay_data = {
                    "id": essay.id,
                    "title": essay.title,
                    "user_id": essay.user_id,
                    "username": user.username if user else None,
                    "status": essay.status,
                    "created_at": essay.created_at.isoformat() if essay.created_at else None,
                    "word_count": essay.word_count,
                    "score": essay.score
                }
                essays.append(essay_data)
            
            return {
                "status": "success",
                "data": {
                    "essays": essays,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "current_page": page,
                    "per_page": per_page
                }
            }
            
        except Exception as e:
            logger.error(f"获取作文列表失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取作文列表失败: {str(e)}"
            }
    
    def get_stats(self, start_date=None, end_date=None):
        """
        获取系统统计数据
        
        Args:
            start_date: 开始日期，默认30天前
            end_date: 结束日期，默认今天
            
        Returns:
            dict: 统计数据
        """
        try:
            # 设置默认时间范围
            if not end_date:
                end_date = datetime.now()
            else:
                end_date = datetime.fromisoformat(end_date)
            
            if not start_date:
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime.fromisoformat(start_date)
            
            # 用户统计
            total_users = User.query.count()
            new_users = User.query.filter(User.created_at.between(start_date, end_date)).count()
            
            # 作文统计
            total_essays = Essay.query.count()
            new_essays = Essay.query.filter(Essay.created_at.between(start_date, end_date)).count()
            
            # 订阅统计
            total_subscriptions = Subscription.query.filter_by(is_active=True).count()
            new_subscriptions = Subscription.query.filter(
                Subscription.created_at.between(start_date, end_date),
                Subscription.is_active == True
            ).count()
            
            # 收入统计
            total_revenue = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
            period_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
                Payment.created_at.between(start_date, end_date)
            ).scalar() or 0
            
            return {
                "status": "success",
                "data": {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "users": {
                        "total": total_users,
                        "new": new_users,
                        "growth_rate": (new_users / total_users * 100) if total_users > 0 else 0
                    },
                    "essays": {
                        "total": total_essays,
                        "new": new_essays,
                        "growth_rate": (new_essays / total_essays * 100) if total_essays > 0 else 0
                    },
                    "subscriptions": {
                        "total": total_subscriptions,
                        "new": new_subscriptions,
                        "growth_rate": (new_subscriptions / total_subscriptions * 100) if total_subscriptions > 0 else 0
                    },
                    "revenue": {
                        "total": float(total_revenue),
                        "period": float(period_revenue)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取统计数据失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取统计数据失败: {str(e)}"
            }
    
    def get_system_config(self):
        """
        获取系统配置
        
        Returns:
            dict: 系统配置
        """
        try:
            # 从配置中获取系统设置
            from app.config import APP_CONFIG, AI_CONFIG
            
            return {
                "status": "success",
                "data": {
                    "app": {
                        "name": APP_CONFIG.get("APP_NAME", "作文批改系统"),
                        "version": APP_CONFIG.get("APP_VERSION", "2.0.0"),
                        "debug_mode": APP_CONFIG.get("DEV_MODE", False)
                    },
                    "ai": {
                        "model": AI_CONFIG.get("MODEL_NAME", "GPT-3.5"),
                        "max_tokens": AI_CONFIG.get("MAX_TOKENS", 4096),
                        "timeout": AI_CONFIG.get("TIMEOUT", 30)
                    },
                    "membership": {
                        "free_monthly_limit": APP_CONFIG.get("FREE_MONTHLY_LIMIT", 5),
                        "free_daily_limit": APP_CONFIG.get("FREE_DAILY_LIMIT", 1),
                        "default_monthly_limit": APP_CONFIG.get("DEFAULT_MONTHLY_LIMIT", 30)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取系统配置失败: {str(e)}")
            return {
                "status": "error",
                "message": f"获取系统配置失败: {str(e)}"
            }
    
    def update_system_config(self, config_data):
        """
        更新系统配置
        
        Args:
            config_data: 配置数据
            
        Returns:
            dict: 操作结果
        """
        try:
            # 在实际应用中，这里需要实现配置的持久化存储
            # 简化处理，记录更新尝试
            logger.info(f"尝试更新系统配置: {config_data}")
            
            return {
                "status": "success",
                "message": "系统配置已更新",
                "data": config_data
            }
            
        except Exception as e:
            logger.error(f"更新系统配置失败: {str(e)}")
            return {
                "status": "error",
                "message": f"更新系统配置失败: {str(e)}"
            }
    
    def change_user_membership(self, user_id, new_plan_code=None, new_end_date_str=None):
        """
        修改用户的会员计划和/或到期时间

        Args:
            user_id: 用户ID
            new_plan_code: 新的会员计划代码 (e.g., 'basic', 'premium') (可选)
            new_end_date_str: 新的到期日期字符串 (YYYY-MM-DD) (可选)

        Returns:
            dict: 操作结果
        """
        try:
            # 查找用户的当前会员记录
            membership = Membership.query.filter_by(user_id=user_id).first()
            if not membership:
                # 如果用户没有会员记录，可能需要先创建，或返回错误
                # 这里假设必须先有会员记录才能修改
                return {
                    "status": "error",
                    "message": f"用户 {user_id} 没有找到有效的会员记录"
                }

            updated = False
            # 更新会员计划
            if new_plan_code:
                new_plan = MembershipPlan.query.filter_by(code=new_plan_code, is_active=True).first()
                if not new_plan:
                    return {"status": "error", "message": f"无效或非活动的会员计划代码: {new_plan_code}"}
                if membership.plan_id != new_plan.id:
                    membership.plan_id = new_plan.id
                    # 可选：重置使用统计?
                    # membership.essays_used_today = 0
                    # membership.essays_used_total = 0
                    updated = True
                    logger.info(f"用户 {user_id} 的会员计划已更新为 {new_plan_code}")

            # 更新到期日期
            if new_end_date_str:
                try:
                    new_end_date = datetime.strptime(new_end_date_str, '%Y-%m-%d')
                    # 通常将到期时间设为当天的结束
                    new_end_date = new_end_date.replace(hour=23, minute=59, second=59)
                    if membership.end_date != new_end_date:
                        membership.end_date = new_end_date
                        # 如果延长了日期，确保状态是激活的
                        if new_end_date > datetime.utcnow() and not membership.is_active:
                             membership.is_active = True
                        updated = True
                        logger.info(f"用户 {user_id} 的会员到期日期已更新为 {new_end_date_str}")
                except ValueError:
                    return {"status": "error", "message": "无效的日期格式，请使用 YYYY-MM-DD"}

            if updated:
                db.session.commit()
                return {"status": "success", "message": "用户会员信息已更新"}
            else:
                return {"status": "success", "message": "未提供有效更新或信息无变化"}

        except Exception as e:
            db.session.rollback()
            logger.error(f"更新用户 {user_id} 会员信息失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"更新用户会员信息失败: {str(e)}"} 