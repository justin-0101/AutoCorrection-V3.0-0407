#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户服务模块
处理用户相关的业务逻辑，如查询、创建、更新等
"""

import logging
from app.models.user import User
from app.models.db import db

logger = logging.getLogger(__name__)

class UserService:
    """用户服务类"""

    @staticmethod
    def get_user_by_id(user_id: int) -> User | None:
        """根据ID获取用户"""
        try:
            return db.session.get(User, user_id)
        except Exception as e:
            logger.error(f"获取用户 ID={user_id} 时出错: {e}", exc_info=True)
            return None

    @staticmethod
    def get_user_by_username(username: str) -> User | None:
        """根据用户名获取用户"""
        try:
            return db.session.query(User).filter_by(username=username).first()
        except Exception as e:
            logger.error(f"获取用户 username={username} 时出错: {e}", exc_info=True)
            return None
            
    @staticmethod
    def get_user_by_email(email: str) -> User | None:
        """根据邮箱获取用户"""
        try:
            return db.session.query(User).filter_by(email=email).first()
        except Exception as e:
            logger.error(f"获取用户 email={email} 时出错: {e}", exc_info=True)
            return None

    # 可以在这里添加更多用户相关的服务方法，例如创建用户、更新用户资料等 