#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
认证服务
提供用户认证、授权、登录、注册等功能
"""

import logging
import secrets
import jwt
from datetime import datetime, timedelta
from flask import current_app, g, request
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import Optional

from app.models import db, User, Role, Permission
from app.utils.exceptions import AuthenticationError, AuthorizationError, ValidationError
from app.core.services import get_redis_service

logger = logging.getLogger(__name__)

class AuthService:
    """认证服务类"""
    
    TOKEN_EXPIRE_DAYS = 7  # 令牌过期时间（天）
    
    @staticmethod
    def authenticate(username_or_email: str, password: str) -> Optional[User]:
        """
        验证用户凭据并返回用户对象
        :param username_or_email: 用户名或邮箱
        :param password: 密码
        :return: 验证成功返回用户对象，失败返回None
        """
        try:
            # 输入验证
            if not username_or_email or not password:
                logger.warning("用户名/邮箱或密码为空")
                return None

            username_or_email = username_or_email.strip()
            
            # 尝试通过用户名或邮箱查找用户
            user = User.query.filter(
                or_(
                    User.username == username_or_email,
                    User.email == username_or_email
                ),
                User.is_deleted == False
            ).first()

            if not user:
                logger.warning(f"用户不存在: {username_or_email}")
                return None

            if not user._is_active:
                logger.warning(f"用户账号已禁用: {username_or_email}")
                return None

            if not user.check_password(password):
                logger.warning(f"密码错误: {username_or_email}")
                return None

            logger.info(f"用户认证成功: {username_or_email}")
            return user

        except Exception as e:
            logger.error(f"认证过程发生错误: {str(e)}")
            return None
    
    @staticmethod
    def register(username: str, email: str, password: str, name: str = None) -> Optional[dict]:
        """
        注册新用户
        :param username: 用户名
        :param email: 邮箱
        :param password: 密码
        :param name: 显示名称（可选）
        :return: 注册成功返回用户信息字典，失败返回None
        """
        try:
            # 输入验证
            if not username or not email or not password:
                raise ValidationError("用户名、邮箱和密码都不能为空")

            username = username.strip()
            email = email.strip()
            
            # 验证用户名和邮箱是否已存在
            if User.query.filter_by(username=username).first():
                raise ValidationError("用户名已存在")
            
            if User.query.filter_by(email=email).first():
                raise ValidationError("邮箱已被注册")
            
            # 创建新用户
            user = User(
                username=username,
                email=email,
                name=name or username,
                _is_active=True,  # 确保使用正确的字段名
                is_deleted=False
            )
            user.set_password(password)
            
            try:
                # 添加默认角色
                student_role = Role.query.filter_by(name='student').first()
                if student_role:
                    from app.models.user import UserRole
                    user_role = UserRole(user=user, role=student_role)
                    db.session.add(user_role)
                
                db.session.add(user)
                db.session.commit()
                
                # 生成访问令牌
                token = AuthService.generate_token(user)
                
                logger.info(f"新用户注册成功: {email}")
                return {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "name": user.name,
                    "token": token,
                    "is_admin": hasattr(user, 'is_admin') and user.is_admin
                }
            except IntegrityError as e:
                db.session.rollback()
                logger.error(f"用户注册失败，数据库错误: {str(e)}")
                raise ValidationError("注册失败，请稍后再试")
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"注册过程发生错误: {str(e)}")
            return None
    
    @staticmethod
    def verify_token(token):
        """验证访问令牌并返回用户对象"""
        if not token:
            logger.warning("未提供令牌")
            return None
            
        try:
            # 解码JWT令牌
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            # 检查令牌是否过期
            exp = datetime.fromtimestamp(payload['exp'])
            if datetime.utcnow() > exp:
                logger.warning("令牌已过期")
                return None
                
            # 检查令牌是否已被撤销
            try:
                redis = get_redis_service()
                if redis and redis.exists(f"revoked_token:{token}"):
                    logger.warning("令牌已被撤销")
                    return None
            except Exception as e:
                logger.error(f"检查令牌撤销状态时出错: {str(e)}")
                # 如果Redis不可用，继续验证其他内容
            
            # 获取用户信息
            user_id = payload.get('sub')
            if not user_id:
                logger.warning("令牌中缺少用户ID")
                return None
                
            user = User.query.filter_by(
                id=user_id,
                is_deleted=False,
                _is_active=True  # 使用正确的字段名
            ).first()
            
            if not user:
                logger.warning(f"令牌对应的用户不存在或已禁用: {user_id}")
                return None
                
            return user
            
        except jwt.ExpiredSignatureError:
            logger.warning("令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的令牌: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"验证令牌时发生未知错误: {str(e)}")
            return None
    
    @staticmethod
    def generate_token(user):
        """生成用户访问令牌"""
        if not user:
            raise ValueError("用户对象不能为空")
            
        now = datetime.utcnow()
        exp = now + timedelta(days=AuthService.TOKEN_EXPIRE_DAYS)
        
        # 创建JWT令牌，尝试安全地获取角色
        try:
            # 首先尝试访问roles属性（由猴子补丁提供）
            if hasattr(user, 'roles'):
                roles = [role.name for role in user.roles if hasattr(role, 'name')]
            # 退回到使用user_roles关系
            elif hasattr(user, 'user_roles'):
                roles = [ur.role.name for ur in user.user_roles if hasattr(ur, 'role') and hasattr(ur.role, 'name')]
            else:
                roles = []
                
            payload = {
                'sub': user.id,  # 用户ID
                'iat': now,      # 签发时间
                'exp': exp,      # 过期时间
                'roles': roles,  # 用户角色
                'is_admin': hasattr(user, 'is_admin') and user.is_admin,  # 管理员标识
                'jti': secrets.token_hex(16)  # 唯一标识符
            }
        except Exception as e:
            logger.warning(f"生成令牌payload时出错，使用最小payload: {str(e)}")
            # 如果出现任何错误，使用最小payload
            payload = {
                'sub': user.id,
                'iat': now,
                'exp': exp,
                'is_admin': getattr(user, 'is_admin', False),
                'jti': secrets.token_hex(16)
            }
        
        try:
            token = jwt.encode(
                payload,
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            
            # 将令牌信息存储在Redis中
            try:
                redis = get_redis_service()
                if redis:
                    token_key = f"user_token:{user.id}"
                    # 将timedelta转换为秒数
                    expire_seconds = int(timedelta(days=AuthService.TOKEN_EXPIRE_DAYS).total_seconds())
                    redis.setex(
                        token_key,
                        expire_seconds,
                        token
                    )
            except Exception as e:
                logger.error(f"存储令牌到Redis时出错: {str(e)}")
                # 如果Redis不可用，继续返回令牌
            
            return token
            
        except Exception as e:
            logger.error(f"生成令牌时发生错误: {str(e)}")
            raise AuthenticationError("生成访问令牌失败")
    
    @staticmethod
    def revoke_token(token):
        """撤销访问令牌"""
        if not token:
            return
            
        try:
            # 将令牌加入撤销列表
            redis = get_redis_service()
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            exp = datetime.fromtimestamp(payload['exp'])
            ttl = (exp - datetime.utcnow()).total_seconds()
            
            if ttl > 0:
                # 使用set方法而不是setex
                redis.setex(
                    f"revoked_token:{token}",
                    int(ttl),  # 直接使用ttl秒数
                    '1'
                )
                
        except jwt.InvalidTokenError:
            pass
    
    @staticmethod
    def get_current_user():
        """获取当前登录用户"""
        user = getattr(g, 'current_user', None)
        if not user:
            return None
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "avatar": user.avatar,
            "is_admin": hasattr(user, 'is_admin') and user.is_admin,
        }
    
    @staticmethod
    def check_permission(user, permission_name):
        """检查用户是否具有指定权限"""
        if not user:
            return False
        
        # 管理员拥有所有权限
        if user.has_role('admin') or user.is_admin:
            return True
        
        # 检查用户角色权限
        return user.has_permission(permission_name)
    
    @staticmethod
    def require_permission(permission_name):
        """检查当前用户是否有指定权限"""
        user = getattr(g, 'current_user', None)
        if not user:
            raise AuthenticationError("需要登录")
        
        if not AuthService.check_permission(user, permission_name):
            logger.warning(f"用户 {user.id} 无权限: {permission_name}")
            raise AuthorizationError(f"没有 {permission_name} 权限")
        
        return True
    
    @staticmethod
    def change_password(user_id, old_password, new_password):
        """修改用户密码"""
        user = User.query.get(user_id)
        if not user:
            raise ValidationError("用户不存在")
        
        if not user.check_password(old_password):
            raise ValidationError("原密码错误")
        
        user.set_password(new_password)
        db.session.commit()
        
        # 撤销所有现有令牌
        redis = get_redis_service()
        token = redis.get(f"user_token:{user.id}")
        if token:
            AuthService.revoke_token(token)
            redis.delete(f"user_token:{user.id}")
        
        logger.info(f"用户 {user_id} 已修改密码")
        return True
    
    @staticmethod
    def reset_password(email, verification_code, new_password):
        """重置用户密码"""
        # 验证验证码
        redis = get_redis_service()
        stored_code = redis.get(f"reset_code:{email}")
        if not stored_code or stored_code.decode() != verification_code:
            raise ValidationError("验证码无效或已过期")
        
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValidationError("用户不存在")
        
        user.set_password(new_password)
        db.session.commit()
        
        # 撤销所有现有令牌
        token = redis.get(f"user_token:{user.id}")
        if token:
            AuthService.revoke_token(token)
            redis.delete(f"user_token:{user.id}")
        
        # 删除验证码
        redis.delete(f"reset_code:{email}")
        
        logger.info(f"用户 {user.id} 已重置密码")
        return True
    
    @staticmethod
    def send_verification_code(email, purpose='registration'):
        """发送验证码"""
        # 生成6位数字验证码
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        
        # 存储验证码（5分钟有效期）
        redis = get_redis_service()
        key = f"reset_code:{email}" if purpose == 'reset_password' else f"reg_code:{email}"
        redis.setex(key, timedelta(minutes=5), code)
        
        # TODO: 实际发送验证码的逻辑
        # 这里应该调用邮件服务发送验证码
        # 目前仅记录日志
        logger.info(f"向 {email} 发送验证码: {code}, 用途: {purpose}")
        
        return code  # 在实际应用中应该移除这个返回值 