#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""AI服务初始化单元测试"""

import unittest
from unittest.mock import patch, MagicMock
import os

from app.core.ai import AIClientFactory, ai_client_factory
from app.core.services.container import container, ServiceScope
from app.core.ai.init_services import init_ai_services, ensure_services

class TestAIServices(unittest.TestCase):
    """测试AI服务初始化功能"""
    
    def setUp(self):
        """测试前设置"""
        # 清理服务容器
        container._services = {}
        # 重置AIClientFactory单例
        AIClientFactory._instance = None
        # 保存环境变量
        self.env_backup = dict(os.environ)
        
    def tearDown(self):
        """测试后清理"""
        # 恢复环境变量
        os.environ.clear()
        os.environ.update(self.env_backup)
        # 清理服务容器
        container._services = {}
        # 重置AIClientFactory单例
        AIClientFactory._instance = None
    
    def test_ai_client_factory_singleton(self):
        """测试AI客户端工厂的单例模式"""
        factory1 = AIClientFactory()
        factory2 = AIClientFactory()
        self.assertIs(factory1, factory2, "AIClientFactory应该是单例")
        
    def test_ai_client_factory_auto_registration(self):
        """测试AI客户端工厂的自动注册功能"""
        factory = AIClientFactory()
        self.assertTrue(
            container.has('ai_client_factory'),
            "AI客户端工厂应该自动注册到服务容器"
        )
        self.assertIs(
            container.get('ai_client_factory'),
            factory,
            "服务容器中的实例应该与创建的实例相同"
        )
    
    def test_init_ai_services_success(self):
        """测试AI服务初始化成功的情况"""
        result = init_ai_services()
        self.assertTrue(result, "AI服务初始化应该成功")
        self.assertTrue(
            container.has('ai_client_factory'),
            "AI客户端工厂应该已注册"
        )
    
    def test_init_ai_services_idempotent(self):
        """测试AI服务初始化的幂等性"""
        # 第一次初始化
        first_result = init_ai_services()
        first_instance = container.get('ai_client_factory')
        
        # 第二次初始化
        second_result = init_ai_services()
        second_instance = container.get('ai_client_factory')
        
        self.assertTrue(first_result and second_result, "两次初始化都应该成功")
        self.assertIs(
            first_instance,
            second_instance,
            "两次初始化应该返回相同的实例"
        )
    
    def test_ensure_services(self):
        """测试ensure_services函数"""
        result = ensure_services()
        self.assertTrue(result, "服务确保函数应该成功执行")
        self.assertTrue(
            container.has('ai_client_factory'),
            "AI客户端工厂应该已注册"
        )
    
    @patch('app.core.services.container.ServiceContainer.register')
    def test_init_ai_services_failure(self, mock_register):
        """测试AI服务初始化失败的情况"""
        # 模拟注册失败
        mock_register.side_effect = Exception("模拟的注册错误")
        
        result = init_ai_services()
        self.assertFalse(result, "初始化失败时应该返回False")
    
    def test_ai_client_factory_default_provider(self):
        """测试AI客户端工厂的默认提供商设置"""
        factory = AIClientFactory()
        client = factory.get_client()  # 不指定提供商
        self.assertIsNotNone(client, "应该返回默认的AI客户端")
    
    def test_ai_client_factory_provider_override(self):
        """测试AI客户端工厂的提供商覆盖功能"""
        # 设置环境变量
        os.environ['AI_PROVIDER'] = 'deepseek'
        
        factory = AIClientFactory()
        client = factory.get_client()
        self.assertIsNotNone(client, "应该返回指定的AI客户端")
    
    def test_ai_client_factory_cache(self):
        """测试AI客户端工厂的缓存功能"""
        factory = AIClientFactory()
        
        # 获取两次相同提供商的客户端
        client1 = factory.get_client('deepseek')
        client2 = factory.get_client('deepseek')
        
        self.assertIs(client1, client2, "相同提供商的客户端应该被缓存")

