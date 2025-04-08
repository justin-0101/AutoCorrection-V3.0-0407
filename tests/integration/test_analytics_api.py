#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
会员分析API的集成测试
测试API路由和响应是否符合预期
"""

import pytest
import json
import datetime
from unittest.mock import patch, MagicMock
from flask_jwt_extended import create_access_token


class TestAnalyticsAPI:
    """会员分析API测试类"""
    
    def test_get_user_usage_stats(self, app, client, test_user):
        """测试获取当前用户的会员使用统计"""
        # 创建访问令牌
        with app.app_context():
            access_token = create_access_token(identity=test_user.id)
        
        # 模拟MembershipAnalytics.get_membership_usage_stats的返回值
        mock_stats = {
            "status": "success",
            "user_id": test_user.id,
            "plan_name": "测试计划",
            "plan_code": "test_plan",
            "days_remaining": 25,
            "usage_stats": {
                "daily": {"used": 2, "limit": 5},
                "total": {"used": 10, "limit": 150}
            }
        }
        
        # 应用模拟对象
        with patch('app.api.v1.analytics.routes.MembershipAnalytics') as mock_analytics:
            # 设置返回值
            mock_analytics.get_membership_usage_stats.return_value = mock_stats
            
            # 发送请求
            response = client.get(
                '/analytics/user/usage',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            # 验证结果
            assert response.status_code == 200
            assert response.json['status'] == 'success'
            assert response.json['user_id'] == test_user.id
            assert 'usage_stats' in response.json
            
            # 验证调用
            mock_analytics.get_membership_usage_stats.assert_called_once_with(test_user.id)
    
    def test_get_user_usage_history(self, app, client, test_user):
        """测试获取当前用户的使用历史记录"""
        # 创建访问令牌
        with app.app_context():
            access_token = create_access_token(identity=test_user.id)
        
        # 模拟UsageAnalytics.get_user_usage_history的返回值
        mock_history = {
            "status": "success",
            "user_id": test_user.id,
            "total_records": 3,
            "usage_logs": [
                {
                    "id": 1,
                    "event_type": "essay_submit",
                    "created_at": "2023-01-01T12:00:00"
                },
                {
                    "id": 2,
                    "event_type": "essay_view",
                    "created_at": "2023-01-02T13:00:00"
                },
                {
                    "id": 3,
                    "event_type": "download_report",
                    "created_at": "2023-01-03T14:00:00"
                }
            ]
        }
        
        # 应用模拟对象
        with patch('app.api.v1.analytics.routes.UsageAnalytics') as mock_analytics:
            # 设置返回值
            mock_analytics.get_user_usage_history.return_value = mock_history
            
            # 测试基本调用
            response = client.get(
                '/analytics/user/history',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            # 验证结果
            assert response.status_code == 200
            assert response.json['status'] == 'success'
            assert response.json['user_id'] == test_user.id
            assert len(response.json['usage_logs']) == 3
            
            # 测试带参数调用
            response = client.get(
                '/analytics/user/history?event_type=essay_submit&start_date=2023-01-01&end_date=2023-01-31&limit=10',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            # 验证结果
            assert response.status_code == 200
    
    def test_get_usage_predictions(self, app, client, test_user):
        """测试获取当前用户的会员使用预测"""
        # 创建访问令牌
        with app.app_context():
            access_token = create_access_token(identity=test_user.id)
        
        # 模拟MembershipAnalytics.get_membership_usage_predictions的返回值
        mock_predictions = {
            "status": "success",
            "user_id": test_user.id,
            "plan_name": "测试计划",
            "days_remaining": 25,
            "daily_average_usage": 1.5,
            "predicted_total_usage": 38,
            "will_exceed_limit": False
        }
        
        # 应用模拟对象
        with patch('app.api.v1.analytics.routes.MembershipAnalytics') as mock_analytics:
            # 设置返回值
            mock_analytics.get_membership_usage_predictions.return_value = mock_predictions
            
            # 发送请求
            response = client.get(
                '/analytics/user/predictions',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            # 验证结果
            assert response.status_code == 200
            assert response.json['status'] == 'success'
            assert response.json['user_id'] == test_user.id
            assert 'predicted_total_usage' in response.json
    
    def test_get_user_engagement(self, app, client, test_user):
        """测试获取当前用户的参与度指标"""
        # 创建访问令牌
        with app.app_context():
            access_token = create_access_token(identity=test_user.id)
        
        # 模拟UsageAnalytics.get_user_engagement_metrics的返回值
        mock_engagement = {
            "status": "success",
            "user_id": test_user.id,
            "username": test_user.username,
            "active_days_last_30": 15,
            "usage_frequency": 2.5,
            "current_streak": 3,
            "engagement_score": 75.5
        }
        
        # 应用模拟对象
        with patch('app.api.v1.analytics.routes.UsageAnalytics') as mock_analytics:
            # 设置返回值
            mock_analytics.get_user_engagement_metrics.return_value = mock_engagement
            
            # 发送请求
            response = client.get(
                '/analytics/user/engagement',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            # 验证结果
            assert response.status_code == 200
            assert response.json['status'] == 'success'
            assert response.json['user_id'] == test_user.id
            assert 'engagement_score' in response.json
    
    def test_admin_endpoints_access_control(self, app, client, test_user):
        """测试管理员API的访问控制"""
        # 创建普通用户访问令牌
        with app.app_context():
            access_token = create_access_token(identity=test_user.id)
        
        # 尝试访问管理员API端点
        admin_endpoints = [
            '/analytics/admin/conversions',
            '/analytics/admin/renewals',
            '/analytics/admin/usage-trends',
            '/analytics/admin/feature-usage?feature=essay_submit',
            '/analytics/admin/quota-alerts',
            f'/analytics/admin/user/{test_user.id}/usage'
        ]
        
        # 应用模拟对象 - 模拟admin_required装饰器的行为
        with patch('app.api.v1.analytics.routes.admin_required') as mock_admin_required:
            # 设置装饰器抛出异常
            mock_admin_required.side_effect = Exception("Authorization error: Admin access required")
            
            # 测试所有管理员端点
            for endpoint in admin_endpoints:
                response = client.get(
                    endpoint,
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                
                # 验证非管理员用户被拒绝访问
                assert response.status_code in [401, 403, 500], f"端点 {endpoint} 没有正确限制访问"
    
    def test_admin_endpoints_with_admin_user(self, app, client):
        """测试管理员API的正常访问"""
        # 创建管理员用户
        from app.models.user import User
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash='admin_hash',
            is_active=True,
            is_admin=True,
            created_at=datetime.datetime.utcnow().timestamp()
        )
        
        with app.app_context():
            app.db.session.add(admin_user)
            app.db.session.commit()
            access_token = create_access_token(identity=admin_user.id)
        
        # 模拟返回值
        mock_stats = {"status": "success", "data": "test"}
        
        # 应用模拟对象
        with patch('app.api.v1.analytics.routes.MembershipAnalytics') as mock_membership_analytics:
            with patch('app.api.v1.analytics.routes.UsageAnalytics') as mock_usage_analytics:
                # 设置返回值
                mock_membership_analytics.get_membership_conversion_stats.return_value = mock_stats
                mock_membership_analytics.get_membership_renewal_stats.return_value = mock_stats
                mock_usage_analytics.get_membership_usage_trends.return_value = mock_stats
                mock_usage_analytics.get_feature_usage_stats.return_value = mock_stats
                mock_usage_analytics.get_usage_quota_alerts.return_value = mock_stats
                mock_membership_analytics.get_membership_usage_stats.return_value = mock_stats
                
                # 测试转化率统计
                response = client.get(
                    '/analytics/admin/conversions',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                assert response.status_code == 200
                
                # 测试续订率统计
                response = client.get(
                    '/analytics/admin/renewals',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                assert response.status_code == 200
                
                # 测试使用趋势统计
                response = client.get(
                    '/analytics/admin/usage-trends',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                assert response.status_code == 200
                
                # 测试功能使用统计
                response = client.get(
                    '/analytics/admin/feature-usage?feature=essay_submit',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                assert response.status_code == 200
                
                # 测试配额警报
                response = client.get(
                    '/analytics/admin/quota-alerts',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                assert response.status_code == 200
                
                # 测试获取特定用户使用统计
                response = client.get(
                    f'/analytics/admin/user/1/usage',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                assert response.status_code == 200 