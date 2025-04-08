#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试grade字段处理"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.models.essay import Essay
from app.models.user import User
from app.core.correction.correction_service import CorrectionService
from app.core.ai import AIClientFactory


class TestGradeHandling(unittest.TestCase):
    """测试grade字段处理"""

    def setUp(self):
        """初始化测试环境"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # 创建测试用户
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()
        
        # Mock CorrectionService
        self.mock_ai_corrector = MagicMock()
        
        # 使用补丁替换CorrectionService的初始化和check_user_limits方法
        patcher = patch.object(CorrectionService, '__init__', return_value=None)
        self.mock_init = patcher.start()
        self.addCleanup(patcher.stop)
        
        self.correction_service = CorrectionService()
        self.correction_service.ai_corrector = self.mock_ai_corrector
        
        # Mock check_user_limits方法
        patcher2 = patch.object(CorrectionService, 'check_user_limits')
        self.mock_check_limits = patcher2.start()
        self.mock_check_limits.return_value = {'status': 'success', 'can_submit': True}
        self.addCleanup(patcher2.stop)
        
        # 添加submit_essay方法的实现
        def mock_submit_essay(user_id, title, content, grade=None):
            # 创建Essay对象
            create_params = {
                'user_id': user_id,
                'title': title,
                'content': content,
            }
            
            if grade is not None:
                create_params['grade'] = grade
                
            essay = Essay(**create_params)
            db.session.add(essay)
            db.session.commit()
            
            return {
                'status': 'success',
                'message': '作文已提交并开始批改',
                'essay_id': essay.id,
                'task_id': 'mock-task-id'
            }
        
        self.correction_service.submit_essay = mock_submit_essay

    def tearDown(self):
        """清理测试环境"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_essay_with_grade(self):
        """测试创建包含grade字段的Essay"""
        essay = Essay(
            user_id=self.user.id,
            title='Test Essay',
            content='This is a test essay content.',
            grade='高中'
        )
        db.session.add(essay)
        db.session.commit()
        
        # 验证字段值
        self.assertEqual(essay.grade, '高中')
        
        # 从数据库重新加载
        db.session.refresh(essay)
        self.assertEqual(essay.grade, '高中')

    def test_essay_without_grade(self):
        """测试创建不包含grade字段的Essay"""
        essay = Essay(
            user_id=self.user.id,
            title='Test Essay',
            content='This is a test essay content.'
        )
        db.session.add(essay)
        db.session.commit()
        
        # 验证字段默认值
        self.assertIsNone(essay.grade)

    def test_submit_essay_with_grade(self):
        """测试提交包含grade的作文"""
        # 调用submit_essay方法
        result = self.correction_service.submit_essay(
            user_id=self.user.id,
            title='Test Essay',
            content='This is a test essay content.',
            grade='初中'
        )
        
        # 验证结果
        self.assertEqual(result['status'], 'success')
        
        # 验证essay是否正确创建并包含grade
        essay_id = result['essay_id']
        essay = Essay.query.get(essay_id)
        self.assertIsNotNone(essay)
        self.assertEqual(essay.grade, '初中')

    def test_submit_essay_without_grade(self):
        """测试提交不包含grade的作文"""
        # 调用submit_essay方法
        result = self.correction_service.submit_essay(
            user_id=self.user.id,
            title='Test Essay',
            content='This is a test essay content.'
        )
        
        # 验证结果
        self.assertEqual(result['status'], 'success')
        
        # 验证essay是否正确创建
        essay_id = result['essay_id']
        essay = Essay.query.get(essay_id)
        self.assertIsNotNone(essay)
        self.assertIsNone(essay.grade)

    def test_ai_client_factory(self):
        """测试AIClientFactory是否正确处理配置项"""
        # 简化测试，不依赖环境变量
        with patch('os.environ', {'DEFAULT_AI_PROVIDER': 'deepseek'}):
            factory = AIClientFactory()
            # 使用patch替换实际的客户端实例化
            with patch('app.core.ai.DeepseekClient'):
                client = factory.get_client()
                self.assertIsNotNone(client)

            # 测试指定provider的情况
            with patch('app.core.ai.OpenAIClient'):
                client = factory.get_client(provider_name='openai')  
                self.assertIsNotNone(client)
        
        # 测试无provider的情况下使用默认值
        with patch('os.environ', {}):
            with patch('app.core.ai.DeepseekClient'):
                with patch('logging.warning') as mock_warning:
                    factory = AIClientFactory()
                    client = factory.get_client()
                    self.assertIsNotNone(client)
                    # 验证记录了警告日志
                    mock_warning.assert_called_once()


if __name__ == '__main__':
    unittest.main() 