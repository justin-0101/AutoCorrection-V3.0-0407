"""
测试AI客户端实现
"""
import unittest
from unittest.mock import patch, MagicMock
import json
import os
import requests

from app.core.ai.open_ai_client import OpenAIClient
from app.core.ai.deepseek_client import DeepseekClient
from app.core.ai.api_client import BaseAPIClient
from app.core.ai import AIClientFactory
from app.core.services import container, ServiceContainer

class TestBaseAPIClient(unittest.TestCase):
    """测试基础API客户端接口"""
    
    def setUp(self):
        """测试前准备"""
        self.client = BaseAPIClient()

    def test_required_result_fields(self):
        """测试必需结果字段"""
        self.assertTrue(isinstance(self.client.REQUIRED_RESULT_FIELDS, list))
        self.assertGreater(len(self.client.REQUIRED_RESULT_FIELDS), 0)

    def test_validate_response(self):
        """测试验证响应功能"""
        # 测试完整响应
        fields = self.client.REQUIRED_RESULT_FIELDS
        complete_response = {field: "value" for field in fields}
        is_valid, missing = self.client.validate_response(complete_response)
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)
        
        # 测试缺失字段
        incomplete_response = {}
        is_valid, missing = self.client.validate_response(incomplete_response)
        self.assertFalse(is_valid)
        self.assertEqual(len(missing), len(fields))

    def test_format_response(self):
        """测试格式化响应功能"""
        result = self.client.format_response({"total_score": 85})
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)
        
        # 测试错误响应
        error_result = self.client.format_response(
            {"error": "测试错误"}, 
            status="error", 
            message="错误信息"
        )
        self.assertEqual(error_result["status"], "error")
        self.assertEqual(error_result["message"], "错误信息")

class TestDeepseekClient(unittest.TestCase):
    """测试Deepseek客户端"""
    
    def setUp(self):
        """测试前准备"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
            self.client = DeepseekClient()
    
    @patch('requests.post')
    def test_analyze_essay_success(self, mock_post):
        """测试成功的作文分析"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "total_score": 85,
                            "content_score": 80,
                            "language_score": 90,
                            "structure_score": 85,
                            "writing_score": 85,
                            "overall_assessment": "这是一篇很好的作文",
                            "content_analysis": "内容充实",
                            "language_analysis": "语言流畅",
                            "structure_analysis": "结构合理",
                            "writing_analysis": "书写整洁",
                            "improvement_suggestions": "可以进一步提高",
                            "spelling_errors": {"错别字": []}
                        })
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 调用方法
        result = self.client.analyze_essay("这是一篇测试作文")
        
        # 验证结果
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["total_score"], 85)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_analyze_essay_api_error(self, mock_post):
        """测试API错误处理"""
        # 模拟API错误
        mock_post.side_effect = requests.exceptions.RequestException("连接错误")
        
        # 调用方法
        result = self.client.analyze_essay("这是一篇测试作文")
        
        # 验证结果
        self.assertEqual(result["status"], "error")
        self.assertIn("连接错误", result["message"])
    
    @patch('requests.post')
    def test_analyze_essay_json_error(self, mock_post):
        """测试JSON解析错误处理"""
        # 模拟无效JSON响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "这不是有效的JSON"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 调用方法
        result = self.client.analyze_essay("这是一篇测试作文")
        
        # 验证结果
        self.assertEqual(result["status"], "error")
        self.assertIn("JSON解析错误", result["message"])
    
    @patch('requests.post')
    def test_analyze_essay_missing_fields(self, mock_post):
        """测试缺少必需字段的处理"""
        # 模拟缺少必需字段的响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "total_score": 85
                            # 缺少其他必需字段
                        })
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 调用方法
        result = self.client.analyze_essay("这是一篇测试作文")
        
        # 验证结果 - 应该使用默认值填充缺失字段
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["total_score"], 85)
        self.assertIn("content_score", result["result"])

class TestOpenAIClient(unittest.TestCase):
    """测试OpenAI客户端"""
    
    def setUp(self):
        """测试前准备"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            self.client = OpenAIClient()
    
    @patch('requests.post')
    def test_analyze_essay_success(self, mock_post):
        """测试成功的作文分析"""
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "total_score": 90,
                            "content_score": 85,
                            "language_score": 95,
                            "structure_score": 90,
                            "writing_score": 90,
                            "overall_assessment": "这是一篇优秀的作文",
                            "content_analysis": "内容丰富",
                            "language_analysis": "语言优美",
                            "structure_analysis": "结构清晰",
                            "writing_analysis": "书写工整",
                            "improvement_suggestions": "继续保持",
                            "spelling_errors": {"错别字": []}
                        })
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 调用方法
        result = self.client.analyze_essay("这是一篇测试作文")
        
        # 验证结果
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["total_score"], 90)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_analyze_essay_api_error(self, mock_post):
        """测试API错误处理"""
        # 模拟API错误
        mock_post.side_effect = requests.exceptions.RequestException("连接错误")
        
        # 调用方法
        result = self.client.analyze_essay("这是一篇测试作文")
        
        # 验证结果
        self.assertEqual(result["status"], "error")
        self.assertIn("连接错误", result["message"])

class TestAIClientFactory(unittest.TestCase):
    """测试AI客户端工厂"""
    
    def setUp(self):
        """测试前准备"""
        # 重置环境
        if 'AI_SERVICE' in os.environ:
            del os.environ['AI_SERVICE']
        
        # 重置工厂实例缓存
        AIClientFactory._instance = None
        self.factory = AIClientFactory()
        
        # 清除容器
        container._services = {}
    
    def test_singleton_pattern(self):
        """测试工厂的单例模式"""
        factory1 = AIClientFactory()
        factory2 = AIClientFactory()
        self.assertIs(factory1, factory2)
    
    def test_get_client_with_deepseek(self):
        """测试获取Deepseek客户端"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
            client = self.factory.get_client('deepseek')
            self.assertIsInstance(client, DeepseekClient)
    
    def test_get_client_with_openai(self):
        """测试获取OpenAI客户端"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            client = self.factory.get_client('openai')
            self.assertIsInstance(client, OpenAIClient)
    
    def test_get_client_caching(self):
        """测试客户端缓存机制"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
            client1 = self.factory.get_client('deepseek')
            client2 = self.factory.get_client('deepseek')
            self.assertIs(client1, client2)  # 应该是同一个实例
    
    def test_get_client_default(self):
        """测试默认客户端选择"""
        with patch.dict('os.environ', {'AI_SERVICE': 'openai', 'OPENAI_API_KEY': 'test_key'}):
            client = self.factory.get_client()  # 不指定类型
            self.assertIsInstance(client, OpenAIClient)
    
    def test_get_client_with_container(self):
        """测试通过服务容器获取客户端"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
            # 使用容器注册工厂
            container.register('ai_client_factory', self.factory)
            
            # 使用容器获取工厂
            factory = container.get('ai_client_factory')
            self.assertIsInstance(factory, AIClientFactory)
            
            # 使用工厂获取客户端
            client = factory.get_client('deepseek')
            self.assertIsInstance(client, DeepseekClient)

if __name__ == '__main__':
    unittest.main() 