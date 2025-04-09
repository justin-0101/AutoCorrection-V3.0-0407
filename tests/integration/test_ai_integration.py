"""
AI服务集成测试
测试与外部AI API的集成
"""

import unittest
import os
import json
from unittest.mock import patch, MagicMock

from app.core.ai import AIClientFactory
from app.core.ai.open_ai_client import OpenAIClient
from app.core.ai.deepseek_client import DeepseekClient
from app.core.ai.aliyun_qianwen_client import AliyunQianwenClient
from app.core.correction.ai_corrector import AICorrectionService
from app.core.services import container

class TestAIServiceIntegration(unittest.TestCase):
    """测试AI服务与外部API的集成"""

    def setUp(self):
        """测试前准备"""
        # 清除容器
        container._services = {}
        
        # 保存原始环境变量
        self.original_env = os.environ.copy()
        
        # 设置测试环境变量
        os.environ['AI_SERVICE'] = 'deepseek'
        os.environ['DEEPSEEK_API_KEY'] = 'sk-c60acce9ffe447438a43485fd8689cc0'  # 使用实际的API密钥
        os.environ['RUN_EXTERNAL_TESTS'] = 'true'  # 启用外部测试
        os.environ['VERIFY_SSL'] = 'false'  # 禁用SSL验证以解决可能的SSL问题
    
    def tearDown(self):
        """测试后清理"""
        # 恢复环境变量
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @unittest.skipUnless(os.environ.get('RUN_EXTERNAL_TESTS'), "跳过外部API测试")
    def test_openai_api_integration(self):
        """测试与OpenAI API的实际集成"""
        # 此测试仅在提供了有效的API密钥时运行
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            self.skipTest("未提供OpenAI API密钥")
        
        # 创建客户端
        client = OpenAIClient(api_key=api_key)
        
        # 测试分析短文
        result = client.analyze_essay("这是一个简短的测试文本，用于验证OpenAI API的集成。")
        
        # 验证结果格式
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)
        self.assertIn("total_score", result["result"])
    
    @unittest.skipUnless(os.environ.get('RUN_EXTERNAL_TESTS'), "跳过外部API测试")
    def test_deepseek_api_integration(self):
        """测试与Deepseek API的实际集成"""
        # 此测试仅在提供了有效的API密钥时运行
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not api_key:
            self.skipTest("未提供Deepseek API密钥")
        
        # 创建客户端
        client = DeepseekClient(api_key=api_key)
        
        # 测试分析短文
        result = client.analyze_essay("这是一个简短的测试文本，用于验证Deepseek API的集成。")
        
        # 验证结果格式
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)
        self.assertIn("total_score", result["result"])
    
    @unittest.skipUnless(os.environ.get('RUN_EXTERNAL_TESTS'), "跳过外部API测试")
    def test_aliyun_qianwen_api_integration(self):
        """测试与阿里云千问 API的实际集成"""
        # 此测试仅在提供了有效的API密钥时运行
        api_key = os.environ.get('ALIYUN_API_KEY')
        if not api_key:
            self.skipTest("未提供阿里云千问 API密钥")
        
        # 创建客户端
        client = AliyunQianwenClient(api_key=api_key)
        
        # 测试分析短文
        result = client.analyze_essay("这是一个简短的测试文本，用于验证阿里云千问 API的集成。")
        
        # 验证结果格式
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)
        self.assertIn("total_score", result["result"])
    
    def test_factory_client_selection(self):
        """测试客户端工厂的选择逻辑"""
        # 测试OpenAI客户端选择
        with patch.dict('os.environ', {'AI_SERVICE': 'openai', 'OPENAI_API_KEY': 'test_key'}):
            factory = AIClientFactory()
            client = factory.get_client()
            self.assertIsInstance(client, OpenAIClient)
        
        # 测试Deepseek客户端选择
        with patch.dict('os.environ', {'AI_SERVICE': 'deepseek', 'DEEPSEEK_API_KEY': 'test_key'}):
            factory = AIClientFactory()
            client = factory.get_client()
            self.assertIsInstance(client, DeepseekClient)
        
        # 测试阿里云千问客户端选择
        with patch.dict('os.environ', {'AI_SERVICE': 'aliyun', 'ALIYUN_API_KEY': 'test_key'}):
            factory = AIClientFactory()
            client = factory.get_client()
            self.assertIsInstance(client, AliyunQianwenClient)
    
    def test_client_caching(self):
        """测试客户端缓存机制"""
        with patch.dict('os.environ', {'AI_SERVICE': 'openai', 'OPENAI_API_KEY': 'test_key'}):
            factory = AIClientFactory()
            client1 = factory.get_client()
            client2 = factory.get_client()
            
            # 验证是同一个实例
            self.assertIs(client1, client2)
    
    def test_correction_service_integration(self):
        """测试批改服务与AI客户端的集成"""
        # 模拟AI客户端
        mock_client = MagicMock()
        mock_client.analyze_essay.return_value = {
            "status": "success",
            "result": {
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
            }
        }
        
        # 模拟工厂
        mock_factory = MagicMock()
        mock_factory.get_client.return_value = mock_client
        
        # 注册到容器
        container.register("ai_client_factory", mock_factory)
        
        # 创建批改服务
        service = AICorrectionService()
        
        # 测试批改功能
        result = service.correct_essay("这是测试文本")
        
        # 验证结果
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["total_score"], 85)
        
        # 验证调用
        mock_factory.get_client.assert_called_once()
        mock_client.analyze_essay.assert_called_once_with("这是测试文本")
    
    def test_client_api_request_integration(self):
        """测试客户端API请求方法的集成"""
        # 创建客户端实例
        with patch.dict('os.environ', {
            'DEEPSEEK_API_KEY': 'sk-c60acce9ffe447438a43485fd8689cc0',
            'VERIFY_SSL': 'false'
        }):
            client = DeepseekClient()
        
        # 模拟requests.post
        with patch('requests.post') as mock_post:
            # 配置模拟响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
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
                }]
            }
            mock_post.return_value = mock_response
            
            # 调用API请求方法
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer sk-c60acce9ffe447438a43485fd8689cc0",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "这是测试文本"}]
            }
            
            response = client._api_request(url, headers, payload)
            
            # 验证请求参数
            mock_post.assert_called_once_with(
                url,
                headers=headers,
                json=payload,
                timeout=30,
                verify=False  # 禁用SSL验证
            )
            
            # 验证响应处理
            self.assertEqual(response.status_code, 200)
            self.assertIn("choices", response.json())
    
    def test_client_extract_result_integration(self):
        """测试客户端结果提取方法的集成"""
        # 创建测试数据
        test_content = json.dumps({
            "total_score": 88,
            "content_score": 85,
            "language_score": 90,
            "structure_score": 87,
            "writing_score": 90,
            "overall_assessment": "这是一篇很好的作文",
            "content_analysis": "内容充实",
            "language_analysis": "语言流畅",
            "structure_analysis": "结构合理",
            "writing_analysis": "书写整洁",
            "improvement_suggestions": "可以进一步提高",
            "spelling_errors": {"错别字": []}
        })
        
        # 创建模拟响应
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": test_content
                    }
                }
            ]
        }
        
        # 测试OpenAI客户端的提取方法
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            client = OpenAIClient()
            result = client._extract_result(mock_response)
            
            # 验证结果
            self.assertEqual(result["total_score"], 88)
            self.assertEqual(result["content_score"], 85)
            self.assertEqual(result["language_score"], 90)
    
    def test_proper_error_handling(self):
        """测试错误处理机制"""
        # 创建客户端
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
            client = DeepseekClient()
        
        # 测试网络错误
        with patch('requests.post') as mock_post:
            # 模拟网络错误
            mock_post.side_effect = Exception("网络连接错误")
            
            # 调用方法
            result = client.analyze_essay("测试文本")
            
            # 验证错误处理
            self.assertEqual(result["status"], "error")
            self.assertIn("网络连接错误", result["message"])
        
        # 测试JSON解析错误
        with patch('requests.post') as mock_post:
            # 模拟无效JSON响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "不是有效的JSON"
                        }
                    }
                ]
            }
            mock_post.return_value = mock_response
            
            # 调用方法
            result = client.analyze_essay("测试文本")
            
            # 验证错误处理
            self.assertEqual(result["status"], "error")
            self.assertIn("JSON", result["message"])

if __name__ == '__main__':
    unittest.main() 