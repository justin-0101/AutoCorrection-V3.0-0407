#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据模型包
"""

# 导入所有模型，使它们对外部可见
from app.models.db import db
from app.models.user import (
    User, Role, Permission, UserProfile, VerificationCode,
    UserRole, RolePermission
)
from app.models.essay import (
    Essay, UserFeedback, EssayTemplate, CorrectionRule, EssayStatus
)
from app.models.correction import Correction
from app.models.membership import (
    MembershipPlan, Membership, Coupon
)
from app.models.subscription import Subscription
from app.models.user_activity import UserActivity
from app.models.notification import Notification, NotificationType
from app.models.usage_log import UsageLog
from app.models.task_status import TaskStatus, TaskState

# 导出所有模型
__all__ = [
    'db',
    'User',
    'Role',
    'Permission',
    'UserProfile',
    'VerificationCode',
    'UserRole',
    'RolePermission',
    'Essay',
    'EssayStatus',
    'Correction',
    'UserFeedback',
    'EssayTemplate',
    'CorrectionRule',
    'MembershipPlan',
    'Membership',
    'Subscription',
    'Coupon',
    'UserActivity',
    'Notification',
    'NotificationType',
    'UsageLog',
    'TaskStatus',
    'TaskState'
] 