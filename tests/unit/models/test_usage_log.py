#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UsageLog模型的单元测试
"""

import pytest
import datetime
from unittest.mock import patch, MagicMock
from app.models.usage_log import UsageLog


class TestUsageLog:
    """使用日志模型测试类"""
    
    def test_create_log(self, test_user, test_membership, session):
        """测试创建使用日志功能"""
        # 准备测试数据
        user_id = test_user.id
        event_type = "essay_submit"
        resource_id = 123
        metadata = {"title": "测试作文", "word_count": 500}
        
        # 模拟Membership查询
        with patch('app.models.usage_log.Membership') as mock_membership_model:
            # 设置模拟对象
            mock_membership = MagicMock()
            mock_membership.id = 1
            mock_membership_model.query.filter_by.return_value.first.return_value = mock_membership
            
            # 调用测试方法
            log = UsageLog.create_log(user_id, event_type, resource_id, metadata)
            
            # 验证结果
            assert log.user_id == user_id
            assert log.membership_id == mock_membership.id
            assert log.event_type == event_type
            assert log.resource_id == resource_id
            assert log.metadata == metadata
    
    def test_create_log_no_membership(self, test_user, session):
        """测试无会员信息时创建使用日志功能"""
        # 准备测试数据
        user_id = test_user.id
        event_type = "essay_view"
        
        # 模拟Membership查询返回None
        with patch('app.models.usage_log.Membership') as mock_membership_model:
            mock_membership_model.query.filter_by.return_value.first.return_value = None
            
            # 调用测试方法
            log = UsageLog.create_log(user_id, event_type)
            
            # 验证结果
            assert log.user_id == user_id
            assert log.membership_id is None
            assert log.event_type == event_type
            assert log.metadata == {}
    
    def test_get_user_logs(self, test_user, session):
        """测试获取用户日志功能"""
        # 创建测试日志数据
        logs = []
        now = datetime.datetime.utcnow()
        
        for i in range(5):
            log = UsageLog(
                user_id=test_user.id,
                event_type=f"event_{i}",
                created_at=(now - datetime.timedelta(days=i)).timestamp()
            )
            session.add(log)
            logs.append(log)
        
        session.commit()
        
        # 测试基本调用
        result = UsageLog.get_user_logs(test_user.id)
        assert len(result) == 5
        
        # 测试事件类型过滤
        result = UsageLog.get_user_logs(test_user.id, event_type="event_0")
        assert len(result) == 1
        assert result[0].event_type == "event_0"
        
        # 测试日期过滤
        start_date = now - datetime.timedelta(days=3)
        result = UsageLog.get_user_logs(test_user.id, start_date=start_date)
        assert len(result) == 4  # 包括今天和前3天
        
        end_date = now - datetime.timedelta(days=2)
        result = UsageLog.get_user_logs(test_user.id, start_date=start_date, end_date=end_date)
        assert len(result) == 2  # 只包括前2天和前3天
        
        # 测试限制条数
        result = UsageLog.get_user_logs(test_user.id, limit=2)
        assert len(result) == 2
    
    def test_get_event_stats(self, test_user, session):
        """测试获取事件统计功能"""
        # 创建测试日志数据
        event_type = "test_event"
        now = datetime.datetime.utcnow()
        
        # 创建多个用户的同类型事件
        for i in range(3):
            for j in range(2):  # 每个用户2条记录
                log = UsageLog(
                    user_id=100 + i,
                    event_type=event_type,
                    created_at=(now - datetime.timedelta(days=j)).timestamp()
                )
                session.add(log)
        
        # 创建不同类型的事件
        for i in range(2):
            log = UsageLog(
                user_id=test_user.id,
                event_type="other_event",
                created_at=(now - datetime.timedelta(days=i)).timestamp()
            )
            session.add(log)
        
        session.commit()
        
        # 测试基本调用
        stats = UsageLog.get_event_stats(event_type)
        assert stats["total_count"] == 6  # 3个用户，每个2条记录
        assert stats["unique_users"] == 3
        
        # 测试日期过滤
        start_date = now - datetime.timedelta(hours=12)  # 只包括今天的记录
        stats = UsageLog.get_event_stats(event_type, start_date=start_date)
        assert stats["total_count"] == 3  # 每个用户今天各有1条记录
        
        # 应该没有更早的记录
        end_date = now - datetime.timedelta(days=5)
        stats = UsageLog.get_event_stats(event_type, end_date=end_date)
        assert stats["total_count"] == 0
    
    def test_model_relationships(self, test_user, test_membership, session):
        """测试模型关系"""
        # 创建使用日志
        log = UsageLog(
            user_id=test_user.id,
            membership_id=test_membership.id,
            event_type="test_event",
            created_at=datetime.datetime.utcnow().timestamp()
        )
        session.add(log)
        session.commit()
        
        # 测试与用户的关系
        assert log.user.id == test_user.id
        
        # 测试与会员的关系
        assert log.membership.id == test_membership.id
        
        # 测试反向关系
        assert log in test_user.usage_logs
        assert log in test_membership.usage_logs 