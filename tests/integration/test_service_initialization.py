import unittest
import os
import json
from flask import Flask
from app import create_app
from app.core.ai.init_services import ensure_services, init_ai_services
from app.core.services.container import container
from app.tasks.celery_app import celery_app

class TestServiceInitialization(unittest.TestCase):
    """测试服务初始化功能"""
    
    def setUp(self):
        """测试前设置"""
        # 设置为测试环境
        os.environ['FLASK_ENV'] = 'testing'
        # 创建测试应用
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        # 清空服务容器
        container.clear()
    
    def tearDown(self):
        """测试后清理"""
        # 删除应用上下文
        self.app_context.pop()
        # 清空服务容器
        container.clear()
    
    def test_init_ai_services(self):
        """测试AI服务初始化功能"""
        # 确保服务容器是空的
        self.assertIsNone(container.get("ai_client_factory"), "容器应该为空")
        
        # 执行AI服务初始化
        result = init_ai_services()
        
        # 验证初始化成功
        self.assertTrue(result, "AI服务初始化应当成功")
        
        # 验证服务已注册
        ai_factory = container.get("ai_client_factory")
        self.assertIsNotNone(ai_factory, "AI客户端工厂应该已注册")
        
        # 验证服务功能
        ai_client = ai_factory.get_client("deepseek")
        self.assertIsNotNone(ai_client, "应该能够获取deepseek AI客户端")
    
    def test_ensure_services(self):
        """测试确保所有服务已初始化的功能"""
        # 确保服务容器是空的
        self.assertIsNone(container.get("ai_client_factory"), "容器应该为空")
        
        # 执行服务初始化
        result = ensure_services()
        
        # 验证初始化成功
        self.assertTrue(result, "服务初始化应当成功")
        
        # 验证AI服务已注册
        ai_factory = container.get("ai_client_factory")
        self.assertIsNotNone(ai_factory, "AI客户端工厂应该已注册")
    
    def test_worker_process_init(self):
        """测试Celery工作进程初始化功能"""
        from app.tasks.celery_app import init_worker_process
        
        # 清空服务容器
        container.clear()
        
        # 模拟Celery工作进程初始化
        init_worker_process(None)
        
        # 验证AI服务已注册
        ai_factory = container.get("ai_client_factory")
        self.assertIsNotNone(ai_factory, "AI客户端工厂应该已在工作进程初始化时注册")

if __name__ == '__main__':
    unittest.main() 