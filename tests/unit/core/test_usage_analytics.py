#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UsageAnalytics服务的单元测试
"""

import pytest
import datetime
from unittest.mock import patch, MagicMock
from app.core.analytics.usage_analytics import UsageAnalytics


class TestUsageAnalytics:
    """使用统计服务测试类"""
    
    def test_log_usage_event(self, test_user, test_membership, monkeypatch):
        """测试记录使用事件功能"""
        # 准备测试数据
        user_id = test_user.id
        event_type = "essay_submit"
        resource_id = 123
        metadata = {"title": "测试作文", "word_count": 500}
        
        # 模拟Membership查询
        mock_membership = MagicMock()
        mock_membership.id = 1
        
        # 模拟UsageLog创建
        mock_usage_log = MagicMock()
        mock_usage_log.id = 999
        
        # 应用模拟对象
        with patch('app.core.analytics.usage_analytics.Membership') as mock_membership_model:
            with patch('app.core.analytics.usage_analytics.UsageLog') as mock_usage_log_class:
                with patch('app.core.analytics.usage_analytics.db') as mock_db:
                    # 设置返回值
                    mock_membership_model.query.filter_by.return_value.first.return_value = mock_membership
                    mock_usage_log_class.return_value = mock_usage_log
                    
                    # 执行测试功能
                    result = UsageAnalytics.log_usage_event(user_id, event_type, resource_id, metadata)
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert 'usage_log_id' in result
                    
                    # 验证调用
                    mock_membership_model.query.filter_by.assert_called_once_with(user_id=user_id)
                    mock_db.session.add.assert_called_once()
                    mock_db.session.commit.assert_called_once()
                    
                    # 如果是essay_submit事件，应该增加使用计数
                    if event_type == 'essay_submit':
                        assert mock_membership.increment_usage.called
    
    def test_log_usage_event_no_membership(self, test_user, monkeypatch):
        """测试记录使用事件时会员不存在的情况"""
        # 准备测试数据
        user_id = test_user.id
        event_type = "essay_view"
        
        # 应用模拟对象
        with patch('app.core.analytics.usage_analytics.Membership') as mock_membership_model:
            # 设置返回None
            mock_membership_model.query.filter_by.return_value.first.return_value = None
            
            # 执行测试功能
            result = UsageAnalytics.log_usage_event(user_id, event_type)
            
            # 验证结果
            assert result['status'] == 'error'
            assert '未找到会员信息' in result['message']
    
    def test_get_user_usage_history(self, test_user, monkeypatch):
        """测试获取用户使用历史功能"""
        # 准备测试数据
        user_id = test_user.id
        mock_logs = []
        now = datetime.datetime.utcnow()
        
        # 创建模拟日志数据
        for i in range(5):
            mock_log = MagicMock()
            mock_log.id = i + 1
            mock_log.event_type = "essay_submit" if i % 2 == 0 else "essay_view"
            mock_log.resource_id = 100 + i
            mock_log.metadata = {"test": f"data_{i}"}
            mock_log.created_at = (now - datetime.timedelta(days=i)).timestamp()
            mock_logs.append(mock_log)
        
        # 应用模拟对象
        with patch('app.core.analytics.usage_analytics.UsageLog') as mock_usage_log_model:
            # 设置查询返回值
            mock_query = MagicMock()
            mock_query.filter_by.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = mock_logs
            
            mock_usage_log_model.query = mock_query
            
            # 测试基本调用
            result = UsageAnalytics.get_user_usage_history(user_id)
            
            # 验证结果
            assert result['status'] == 'success'
            assert result['user_id'] == user_id
            assert result['total_records'] == len(mock_logs)
            assert len(result['usage_logs']) == len(mock_logs)
            
            # 测试带过滤条件的调用
            event_type = "essay_submit"
            start_date = now - datetime.timedelta(days=10)
            end_date = now
            limit = 3
            
            result_filtered = UsageAnalytics.get_user_usage_history(
                user_id, event_type, start_date, end_date, limit
            )
            
            # 验证基本结果
            assert result_filtered['status'] == 'success'
    
    def test_get_feature_usage_stats(self, monkeypatch):
        """测试获取特定功能使用统计功能"""
        # 准备测试数据
        feature = "essay_submit"
        period_days = 30
        
        # 模拟UsageLog查询
        mock_events = []
        now = datetime.datetime.utcnow()
        
        for i in range(10):
            mock_event = MagicMock()
            mock_event.user_id = 100 + i % 3  # 使用3个不同的用户ID
            mock_event.created_at = (now - datetime.timedelta(days=i % 7)).timestamp()  # 7天内的数据
            mock_events.append(mock_event)
        
        # 模拟Membership和MembershipPlan查询
        mock_membership = MagicMock()
        mock_membership.plan_id = 1
        
        mock_plan = MagicMock()
        mock_plan.code = "basic"
        
        # 应用模拟对象
        with patch('app.core.analytics.usage_analytics.UsageLog') as mock_usage_log_model:
            with patch('app.core.analytics.usage_analytics.Membership') as mock_membership_model:
                with patch('app.core.analytics.usage_analytics.MembershipPlan') as mock_plan_model:
                    # 设置返回值
                    mock_usage_log_model.query.filter.return_value.all.return_value = mock_events
                    mock_membership_model.query.filter_by.return_value.order_by.return_value.first.return_value = mock_membership
                    mock_plan_model.query.get.return_value = mock_plan
                    
                    # 执行测试功能
                    result = UsageAnalytics.get_feature_usage_stats(feature, period_days)
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert result['feature'] == feature
                    assert result['period_days'] == period_days
                    assert result['total_usage'] == len(mock_events)
                    assert 'unique_users' in result
                    assert 'usage_by_plan' in result
                    assert 'time_series' in result
                    assert 'average_daily_usage' in result
    
    def test_get_membership_usage_trends(self, monkeypatch):
        """测试获取会员使用趋势统计功能"""
        # 准备测试数据
        period_days = 90
        
        # 模拟UsageLog查询
        mock_logs = []
        now = datetime.datetime.utcnow()
        
        for i in range(30):
            mock_log = MagicMock()
            mock_log.user_id = 100 + i % 5  # 5个不同用户
            mock_log.event_type = f"event_{i % 3}"  # 3种不同事件类型
            mock_log.created_at = (now - datetime.timedelta(days=i % 14)).timestamp()  # 14天内的数据
            mock_logs.append(mock_log)
        
        # 模拟Membership和MembershipPlan查询
        mock_membership = MagicMock()
        mock_membership.plan_id = 1
        
        mock_plans = []
        for code in ["basic", "premium", "professional"]:
            mock_plan = MagicMock()
            mock_plan.code = code
            mock_plans.append(mock_plan)
        
        # 应用模拟对象
        with patch('app.core.analytics.usage_analytics.UsageLog') as mock_usage_log_model:
            with patch('app.core.analytics.usage_analytics.Membership') as mock_membership_model:
                with patch('app.core.analytics.usage_analytics.MembershipPlan') as mock_plan_model:
                    # 设置返回值
                    mock_usage_log_model.query.filter.return_value.all.return_value = mock_logs
                    mock_membership_model.query.filter_by.return_value.first.return_value = mock_membership
                    mock_plan_model.query.all.return_value = mock_plans
                    mock_plan_model.query.get.return_value = mock_plans[0]
                    
                    # 执行测试功能
                    result = UsageAnalytics.get_membership_usage_trends(period_days)
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert result['period_days'] == period_days
                    assert result['total_usage'] == len(mock_logs)
                    assert 'event_type_counts' in result
                    assert 'plan_usage_totals' in result
                    assert 'plan_usage_percentages' in result
                    assert 'average_daily_usage' in result
                    assert 'peak_usage' in result
                    assert 'time_series' in result
    
    def test_get_user_engagement_metrics(self, test_user, test_membership, monkeypatch):
        """测试获取用户参与度指标功能"""
        # 准备测试数据
        user_id = test_user.id
        
        # 模拟User查询
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.username = "testuser"
        
        # 模拟Membership查询
        mock_membership = MagicMock()
        mock_membership.plan = MagicMock()
        mock_membership.plan.name = "测试计划"
        
        # 模拟UsageLog查询
        mock_daily_usage = [
            ('2023-01-01', 2),
            ('2023-01-02', 3),
            ('2023-01-03', 1)
        ]
        
        mock_logs = []
        now = datetime.datetime.utcnow()
        
        for i in range(10):
            mock_log = MagicMock()
            mock_log.created_at = (now - datetime.timedelta(days=i)).timestamp()
            mock_logs.append(mock_log)
        
        # 模拟活跃日期
        active_dates = set([
            now.strftime('%Y-%m-%d'),
            (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
            (now - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        ])
        
        # 模拟功能使用统计
        mock_top_features = [
            ('essay_submit', 10),
            ('essay_view', 5),
            ('download_report', 3)
        ]
        
        # 应用模拟对象
        with patch('app.core.analytics.usage_analytics.User') as mock_user_model:
            with patch('app.core.analytics.usage_analytics.Membership') as mock_membership_model:
                with patch('app.core.analytics.usage_analytics.UsageLog') as mock_usage_log_model:
                    with patch('app.core.analytics.usage_analytics.db') as mock_db:
                        # 设置返回值
                        mock_user_model.query.get.return_value = mock_user
                        mock_membership_model.query.filter_by.return_value.first.return_value = mock_membership
                        
                        # 设置日期查询
                        mock_db.session.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_daily_usage
                        
                        # 设置活跃日查询
                        mock_usage_log_model.query.filter_by.return_value.order_by.return_value.all.return_value = mock_logs
                        
                        # 设置功能统计
                        mock_db.session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_top_features
                        
                        # 设置月度活跃
                        mock_usage_log_model.query.filter.return_value.first.return_value = mock_logs[0]
                        
                        # 执行测试功能
                        result = UsageAnalytics.get_user_engagement_metrics(user_id)
                        
                        # 验证结果
                        assert result['status'] == 'success'
                        assert result['user_id'] == user_id
                        assert result['username'] == mock_user.username
                        assert 'membership_level' in result
                        assert 'active_days_last_30' in result
                        assert 'active_percentage_last_30' in result
                        assert 'usage_frequency' in result
                        assert 'current_streak' in result
                        assert 'max_streak' in result
                        assert 'retained' in result
                        assert 'top_features_used' in result
                        assert 'engagement_score' in result
    
    def test_get_usage_quota_alerts(self, monkeypatch):
        """测试获取使用配额警报功能"""
        # 准备测试数据
        
        # 模拟活跃会员
        mock_memberships = []
        for i in range(5):
            mock_membership = MagicMock()
            mock_membership.id = i + 1
            mock_membership.user_id = 100 + i
            mock_membership.plan_id = 1
            
            # 设置不同使用量
            if i < 2:
                # 接近每日配额
                mock_membership.essays_used_today = 4
            else:
                # 接近总配额
                mock_membership.essays_used_total = 140
            
            mock_memberships.append(mock_membership)
        
        # 模拟会员计划
        mock_plan = MagicMock()
        mock_plan.max_essays_per_day = 5
        mock_plan.max_essays_total = 150
        
        # 模拟用户
        mock_user = MagicMock()
        mock_user.id = 101
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        
        # 应用模拟对象
        with patch('app.core.analytics.usage_analytics.Membership') as mock_membership_model:
            with patch('app.core.analytics.usage_analytics.MembershipPlan') as mock_plan_model:
                with patch('app.core.analytics.usage_analytics.User') as mock_user_model:
                    # 设置返回值
                    mock_membership_model.query.filter_by.return_value.all.return_value = mock_memberships
                    mock_plan_model.query.get.return_value = mock_plan
                    mock_user_model.query.get.return_value = mock_user
                    
                    # 执行测试功能
                    result = UsageAnalytics.get_usage_quota_alerts()
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert 'alerts_count' in result
                    assert 'users_at_limit' in result
                    assert isinstance(result['users_at_limit'], list) 