#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员分析与统计流程的端到端测试
模拟用户使用流程，测试会员使用统计、分析和预测功能
"""

import pytest
import datetime
import json
from flask_jwt_extended import create_access_token
from app.models.usage_log import UsageLog
from app.core.analytics.usage_analytics import UsageAnalytics


class TestMembershipWorkflow:
    """会员使用流程测试类"""
    
    def test_complete_user_workflow(self, app, client, test_user, test_membership, test_membership_plan, test_essays, session):
        """测试完整的用户使用流程和分析功能"""
        with app.app_context():
            # 创建访问令牌
            access_token = create_access_token(identity=test_user.id)
            
            # 步骤1: 记录一系列用户使用事件
            self._record_usage_events(test_user.id, client, access_token)
            
            # 步骤2: 获取和验证用户的使用统计数据
            self._verify_usage_statistics(client, access_token, test_user.id)
            
            # 步骤3: 获取和验证用户的参与度指标
            self._verify_engagement_metrics(client, access_token, test_user.id)
            
            # 步骤4: 获取和验证用户的使用预测
            self._verify_usage_predictions(client, access_token, test_user.id)
            
            # 步骤5: 获取和验证用户的使用历史记录
            self._verify_usage_history(client, access_token, test_user.id)
    
    def _record_usage_events(self, user_id, client, access_token):
        """记录一系列用户使用事件"""
        # 记录不同类型的使用事件
        event_types = [
            {"type": "essay_submit", "resource_id": 101, "metadata": {"title": "测试作文1", "word_count": 500}},
            {"type": "essay_view", "resource_id": 101, "metadata": {"view_time": 120}},
            {"type": "essay_submit", "resource_id": 102, "metadata": {"title": "测试作文2", "word_count": 650}},
            {"type": "download_report", "resource_id": 101, "metadata": {"format": "pdf"}},
            {"type": "essay_view", "resource_id": 102, "metadata": {"view_time": 90}}
        ]
        
        # 使用API记录事件
        for event in event_types:
            # 这里我们直接调用服务，因为可能没有专门的API端点来记录事件
            UsageAnalytics.log_usage_event(
                user_id=user_id, 
                event_type=event["type"], 
                resource_id=event["resource_id"], 
                metadata=event["metadata"]
            )
            
            # 验证事件被正确记录
            logs = UsageLog.query.filter_by(
                user_id=user_id, 
                event_type=event["type"],
                resource_id=event["resource_id"]
            ).all()
            
            assert len(logs) > 0, f"事件 {event['type']} 未被正确记录"
    
    def _verify_usage_statistics(self, client, access_token, user_id):
        """获取和验证用户的使用统计数据"""
        # 调用API获取使用统计
        response = client.get(
            '/analytics/user/usage',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 基本验证
        assert data['status'] == 'success'
        assert data['user_id'] == user_id
        assert 'usage_stats' in data
        assert 'daily' in data['usage_stats']
        assert 'total' in data['usage_stats']
        
        # 验证使用数据
        assert 'usage_history' in data
        assert isinstance(data['usage_history'], list)
        assert len(data['usage_history']) > 0
    
    def _verify_engagement_metrics(self, client, access_token, user_id):
        """获取和验证用户的参与度指标"""
        # 调用API获取参与度指标
        response = client.get(
            '/analytics/user/engagement',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 基本验证
        assert data['status'] == 'success'
        assert data['user_id'] == user_id
        
        # 验证参与度数据
        assert 'active_days_last_30' in data
        assert 'usage_frequency' in data
        assert 'current_streak' in data
        assert 'engagement_score' in data
        assert 'top_features_used' in data
        
        # 验证参与度分数合理性
        assert 0 <= data['engagement_score'] <= 100
    
    def _verify_usage_predictions(self, client, access_token, user_id):
        """获取和验证用户的使用预测"""
        # 调用API获取使用预测
        response = client.get(
            '/analytics/user/predictions',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 基本验证
        assert data['status'] == 'success'
        assert data['user_id'] == user_id
        
        # 验证预测数据
        assert 'days_remaining' in data
        assert 'daily_average_usage' in data
        assert 'predicted_total_usage' in data
        assert 'will_exceed_limit' in data
        
        # 验证预测的合理性
        assert data['days_remaining'] >= 0
        assert data['daily_average_usage'] >= 0
        assert data['predicted_total_usage'] >= 0
    
    def _verify_usage_history(self, client, access_token, user_id):
        """获取和验证用户的使用历史记录"""
        # 调用API获取使用历史
        response = client.get(
            '/analytics/user/history',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 基本验证
        assert data['status'] == 'success'
        assert data['user_id'] == user_id
        
        # 验证历史数据
        assert 'total_records' in data
        assert 'usage_logs' in data
        assert isinstance(data['usage_logs'], list)
        
        # 验证我们之前记录的事件存在
        event_types = set([log['event_type'] for log in data['usage_logs']])
        assert 'essay_submit' in event_types
        assert 'essay_view' in event_types


class TestAdminAnalyticsWorkflow:
    """管理员分析流程测试类"""
    
    def test_admin_analytics_workflow(self, app, client, test_user, test_membership, test_membership_plan, test_essays, session):
        """测试管理员分析流程"""
        with app.app_context():
            # 创建管理员用户
            from app.models.user import User
            admin_user = User(
                username='admin_test',
                email='admin_test@example.com',
                password_hash='admin_hash',
                is_active=True,
                is_admin=True,
                created_at=datetime.datetime.utcnow().timestamp()
            )
            session.add(admin_user)
            session.commit()
            
            # 创建管理员令牌
            admin_token = create_access_token(identity=admin_user.id)
            
            # 记录一些使用事件以便有数据可分析
            self._create_test_data(session, test_user.id)
            
            # 测试各种管理员分析接口
            self._verify_conversion_stats(client, admin_token)
            self._verify_renewal_stats(client, admin_token)
            self._verify_usage_trends(client, admin_token)
            self._verify_feature_usage(client, admin_token)
            self._verify_quota_alerts(client, admin_token)
            self._verify_specific_user_usage(client, admin_token, test_user.id)
    
    def _create_test_data(self, session, user_id):
        """创建测试数据"""
        # 创建多个使用日志
        now = datetime.datetime.utcnow()
        
        # 创建不同类型的使用日志
        event_types = ["essay_submit", "essay_view", "download_report"]
        
        for i in range(10):
            for event_type in event_types:
                log = UsageLog(
                    user_id=user_id,
                    event_type=event_type,
                    resource_id=100 + i,
                    created_at=(now - datetime.timedelta(days=i % 5)).timestamp()
                )
                session.add(log)
        
        session.commit()
    
    def _verify_conversion_stats(self, client, admin_token):
        """验证转化率统计接口"""
        response = client.get(
            '/analytics/admin/conversions',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'conversion_rate' in data
        assert 'plan_statistics' in data
    
    def _verify_renewal_stats(self, client, admin_token):
        """验证续订率统计接口"""
        response = client.get(
            '/analytics/admin/renewals',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'overall_renewal_rate' in data
        assert 'plan_statistics' in data
    
    def _verify_usage_trends(self, client, admin_token):
        """验证使用趋势统计接口"""
        response = client.get(
            '/analytics/admin/usage-trends',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'total_usage' in data
        assert 'time_series' in data
    
    def _verify_feature_usage(self, client, admin_token):
        """验证功能使用统计接口"""
        response = client.get(
            '/analytics/admin/feature-usage?feature=essay_submit',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'feature' in data
        assert data['feature'] == 'essay_submit'
        assert 'total_usage' in data
        assert 'time_series' in data
    
    def _verify_quota_alerts(self, client, admin_token):
        """验证配额警报接口"""
        response = client.get(
            '/analytics/admin/quota-alerts',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'alerts_count' in data
        assert 'users_at_limit' in data
    
    def _verify_specific_user_usage(self, client, admin_token, user_id):
        """验证特定用户使用统计接口"""
        response = client.get(
            f'/analytics/admin/user/{user_id}/usage',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'user_id' in data
        assert data['user_id'] == user_id
        assert 'usage_stats' in data 