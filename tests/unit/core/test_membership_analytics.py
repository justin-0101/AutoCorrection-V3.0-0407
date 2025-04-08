#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MembershipAnalytics服务的单元测试
"""

import pytest
import datetime
from unittest.mock import patch, MagicMock
from app.core.analytics.membership_analytics import MembershipAnalytics


class TestMembershipAnalytics:
    """会员分析服务测试类"""
    
    def test_get_membership_usage_stats(self, test_user, test_membership, test_membership_plan, monkeypatch):
        """测试获取会员使用统计功能"""
        # 准备模拟数据
        user_id = test_user.id
        
        # 模拟Membership.query
        mock_membership = MagicMock()
        mock_membership.user_id = test_user.id
        mock_membership.plan_id = test_membership_plan.id
        mock_membership.start_date = datetime.datetime.utcnow()
        mock_membership.end_date = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        mock_membership.is_active = True
        mock_membership.essays_used_today = 2
        mock_membership.essays_used_total = 10
        mock_membership.last_essay_date = datetime.datetime.utcnow().date()
        mock_membership.is_expired.return_value = False
        
        # 模拟MembershipPlan.query
        mock_plan = MagicMock()
        mock_plan.name = test_membership_plan.name
        mock_plan.code = test_membership_plan.code
        mock_plan.max_essays_per_day = 5
        mock_plan.max_essays_total = 150
        
        # 模拟Essay.query
        mock_essays = []
        now = datetime.datetime.utcnow()
        
        for i in range(5):
            mock_essay = MagicMock()
            # 设置不同日期的created_at
            created_date = now - datetime.timedelta(days=i)
            mock_essay.created_at = created_date.timestamp()
            mock_essays.append(mock_essay)
        
        # 应用模拟对象
        with patch('app.core.analytics.membership_analytics.Membership') as mock_membership_model:
            with patch('app.core.analytics.membership_analytics.MembershipPlan') as mock_plan_model:
                with patch('app.core.analytics.membership_analytics.Essay') as mock_essay_model:
                    # 设置查询返回值
                    mock_membership_model.query.filter_by.return_value.first.return_value = mock_membership
                    mock_plan_model.query.get.return_value = mock_plan
                    mock_essay_model.query.filter.return_value.order_by.return_value.all.return_value = mock_essays
                    
                    # 执行测试功能
                    result = MembershipAnalytics.get_membership_usage_stats(user_id)
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert result['user_id'] == user_id
                    assert result['plan_name'] == mock_plan.name
                    assert result['plan_code'] == mock_plan.code
                    assert 'usage_stats' in result
                    assert 'daily' in result['usage_stats']
                    assert 'total' in result['usage_stats']
                    assert result['usage_stats']['daily']['used'] == mock_membership.essays_used_today
                    assert result['usage_stats']['total']['used'] == mock_membership.essays_used_total
                    assert 'usage_history' in result
                    assert len(result['usage_history']) > 0
    
    def test_get_membership_usage_stats_no_membership(self, test_user, monkeypatch):
        """测试当会员信息不存在时的情况"""
        user_id = test_user.id
        
        # 模拟Membership.query返回None
        with patch('app.core.analytics.membership_analytics.Membership') as mock_membership_model:
            mock_membership_model.query.filter_by.return_value.first.return_value = None
            
            # 执行测试功能
            result = MembershipAnalytics.get_membership_usage_stats(user_id)
            
            # 验证结果
            assert result['status'] == 'error'
            assert 'message' in result
            assert '未找到会员信息' in result['message']
    
    def test_get_membership_conversion_stats(self, monkeypatch):
        """测试获取会员转化率统计功能"""
        # 准备模拟数据
        period_days = 30
        total_new_users = 100
        paid_memberships = 30
        expected_conversion_rate = 30.0  # 30/100 * 100 = 30%
        
        # 模拟查询结果
        mock_user_count = MagicMock(return_value=total_new_users)
        mock_membership_count = MagicMock(return_value=paid_memberships)
        
        # 模拟计划转化数据
        mock_plan_conversions = [
            ('basic', '基础会员', 15),
            ('premium', '高级会员', 10),
            ('professional', '专业会员', 5)
        ]
        
        # 模拟每日转化数据
        mock_daily_conversions = [
            ('2023-01-01', 2),
            ('2023-01-02', 3),
            ('2023-01-03', 1)
        ]
        
        # 应用模拟对象
        with patch('app.core.analytics.membership_analytics.User') as mock_user_model:
            with patch('app.core.analytics.membership_analytics.db') as mock_db:
                # 设置用户计数
                mock_user_model.query.filter.return_value.count.return_value = total_new_users
                
                # 设置会员计数
                mock_db.session.query.return_value.join.return_value.filter.return_value.distinct.return_value.count.return_value = paid_memberships
                
                # 设置计划转化数据
                mock_db.session.query.return_value.join.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = mock_plan_conversions
                
                # 设置每日转化数据
                mock_db.session.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = mock_daily_conversions
                
                # 执行测试功能
                result = MembershipAnalytics.get_membership_conversion_stats(period_days)
                
                # 验证结果
                assert result['status'] == 'success'
                assert result['period_days'] == period_days
                assert result['total_new_users'] == total_new_users
                assert result['total_new_memberships'] == paid_memberships
                assert result['conversion_rate'] == expected_conversion_rate
                assert 'plan_statistics' in result
                assert 'time_series' in result
    
    def test_get_membership_renewal_stats(self, monkeypatch):
        """测试获取会员续订率统计功能"""
        # 准备模拟数据
        period_days = 90
        expired_memberships = 50
        renewed_memberships = 20
        expected_renewal_rate = 40.0  # 20/50 * 100 = 40%
        
        # 模拟查询结果
        mock_expired_count = MagicMock(return_value=expired_memberships)
        mock_renewed_count = MagicMock(return_value=renewed_memberships)
        
        # 模拟计划续订数据
        mock_plan_renewals = [
            ('basic', '基础会员', 30, 10),
            ('premium', '高级会员', 15, 8),
            ('professional', '专业会员', 5, 2)
        ]
        
        # 模拟月度续订数据
        mock_monthly_renewals = [
            ('2023-01', 20, 8),
            ('2023-02', 15, 6),
            ('2023-03', 15, 6)
        ]
        
        # 应用模拟对象
        with patch('app.core.analytics.membership_analytics.Membership') as mock_membership_model:
            with patch('app.core.analytics.membership_analytics.db') as mock_db:
                # 设置到期会员计数
                mock_membership_model.query.filter.return_value.count.return_value = expired_memberships
                
                # 设置续订会员计数
                mock_db.session.query.return_value.join.return_value.filter.return_value.distinct.return_value.count.return_value = renewed_memberships
                
                # 设置计划续订数据
                mock_db.session.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.all.return_value = mock_plan_renewals
                
                # 设置月度续订数据
                mock_db.session.query.return_value.outerjoin.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = mock_monthly_renewals
                
                # 执行测试功能
                result = MembershipAnalytics.get_membership_renewal_stats(period_days)
                
                # 验证结果
                assert result['status'] == 'success'
                assert result['period_days'] == period_days
                assert result['total_expired_memberships'] == expired_memberships
                assert result['total_renewed_memberships'] == renewed_memberships
                assert result['overall_renewal_rate'] == expected_renewal_rate
                assert 'plan_statistics' in result
                assert 'monthly_statistics' in result
    
    def test_get_membership_usage_predictions(self, test_user, test_membership, test_membership_plan, monkeypatch):
        """测试获取会员使用预测功能"""
        # 准备模拟数据
        user_id = test_user.id
        days_remaining = 20
        
        # 模拟Membership.query
        mock_membership = MagicMock()
        mock_membership.user_id = test_user.id
        mock_membership.plan_id = test_membership_plan.id
        mock_membership.end_date = datetime.datetime.utcnow() + datetime.timedelta(days=days_remaining)
        mock_membership.essays_used_total = 50
        
        # 模拟MembershipPlan.query
        mock_plan = MagicMock()
        mock_plan.name = test_membership_plan.name
        mock_plan.max_essays_total = 150
        
        # 模拟Essay.query
        mock_essays = []
        now = datetime.datetime.utcnow()
        
        # 创建30天的模拟数据，平均每天1篇
        for i in range(30):
            mock_essay = MagicMock()
            created_date = now - datetime.timedelta(days=i)
            mock_essay.created_at = created_date.timestamp()
            mock_essays.append(mock_essay)
        
        # 应用模拟对象
        with patch('app.core.analytics.membership_analytics.Membership') as mock_membership_model:
            with patch('app.core.analytics.membership_analytics.MembershipPlan') as mock_plan_model:
                with patch('app.core.analytics.membership_analytics.Essay') as mock_essay_model:
                    # 设置查询返回值
                    mock_membership_model.query.filter_by.return_value.first.return_value = mock_membership
                    mock_plan_model.query.get.return_value = mock_plan
                    mock_essay_model.query.filter.return_value.order_by.return_value.all.return_value = mock_essays
                    
                    # 执行测试功能
                    result = MembershipAnalytics.get_membership_usage_predictions(user_id)
                    
                    # 验证结果
                    assert result['status'] == 'success'
                    assert result['user_id'] == user_id
                    assert result['plan_name'] == mock_plan.name
                    assert result['days_remaining'] == days_remaining
                    assert 'daily_average_usage' in result
                    assert 'predicted_total_usage' in result
                    assert 'total_remaining_quota' in result
                    assert 'will_exceed_limit' in result
                    
                    # 验证预测逻辑
                    predicted_usage = result['predicted_total_usage']
                    assert predicted_usage == int(1 * days_remaining)  # 平均每天1篇 * 剩余天数 