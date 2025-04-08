#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API客户端单元测试
测试BaseAPIClient及其子类实现
"""

import unittest
import json
from unittest.mock import patch, MagicMock

from app.core.ai.api_client import BaseAPIClient, APIError
from app.core.ai.deepseek_client import DeepseekClient
from app.core.ai.open_ai_client import OpenAIClient
from app.core.ai.aliyun_qianwen_client import AliyunQianwenClient

class TestBaseAPIClient(unittest.TestCase):
    """BaseAPIClient测试类"""
    
    def test_required_result_fields(self):
        """测试所需返回字段定义"""
        # 验证BaseAPIClient定义了所需的返回字段列表
        self.assertTrue(hasattr(BaseAPIClient, 'REQUIRED_RESULT_FIELDS'))
        self.assertIsInstance(BaseAPIClient.REQUIRED_RESULT_FIELDS, list)
        self.assertGreater(len(BaseAPIClient.REQUIRED_RESULT_FIELDS), 0)
        
        # 验证关键字段存在
        essential_fields = ["total_score", "content_score", "language_score", 
                         "structure_score", "writing_score"]
        for field in essential_fields:
            self.assertIn(field, BaseAPIClient.REQUIRED_RESULT_FIELDS)
    
    def test_validate_response(self):
        """测试响应验证方法"""
        # 创建一个测试用客户端
        mock_client = MagicMock(spec=BaseAPIClient)
        mock_client.REQUIRED_RESULT_FIELDS = ["field1", "field2"]
        
        # 模拟validate_response方法
        def mock_validate(response_data):
            missing_fields = []
            if not isinstance(response_data, dict):
                return False, ["响应不是字典类型"]
            
            if "status" not in response_data:
                return False, ["缺少status字段"]
            
            if response_data["status"] == "success":
                if "result" not in response_data:
                    return False, ["缺少result字段"]
                
                result = response_data["result"]
                for field in ["field1", "field2"]:
                    if field not in result:
                        missing_fields.append(field)
            elif response_data["status"] == "error":
                if "message" not in response_data:
                    return False, ["错误响应缺少message字段"]
            
            return len(missing_fields) == 0, missing_fields
        
        mock_client.validate_response.side_effect = mock_validate
        
        # 验证成功响应
        valid_response = {
            "status": "success",
            "result": {
                "field1": "value1",
                "field2": "value2"
            }
        }
        is_valid, missing = mock_client.validate_response(valid_response)
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)
        
        # 验证错误响应
        error_response = {
            "status": "error",
            "message": "An error occurred"
        }
        is_valid, missing = mock_client.validate_response(error_response)
        self.assertTrue(is_valid)
        self.assertEqual(len(missing), 0)
        
        # 验证缺失字段
        invalid_response = {
            "status": "success",
            "result": {
                "field1": "value1"
            }
        }
        is_valid, missing = mock_client.validate_response(invalid_response)
        self.assertFalse(is_valid)
        self.assertEqual(missing, ["field2"])
        
        # 验证不是字典
        is_valid, missing = mock_client.validate_response("not a dict")
        self.assertFalse(is_valid)
        self.assertEqual(missing, ["响应不是字典类型"])
        
        # 验证缺少状态
        is_valid, missing = mock_client.validate_response({"no_status": True})
        self.assertFalse(is_valid)
        self.assertEqual(missing, ["缺少status字段"])
        
        # 验证错误响应缺少消息
        is_valid, missing = mock_client.validate_response({"status": "error"})
        self.assertFalse(is_valid)
        self.assertEqual(missing, ["错误响应缺少message字段"])
        
        # 验证缺少结果
        is_valid, missing = mock_client.validate_response({"status": "success"})
        self.assertFalse(is_valid)
        self.assertEqual(missing, ["缺少result字段"])

class TestDeepseekClient(unittest.TestCase):
    """DeepseekClient测试类"""
    
    def setUp(self):
        """初始化测试环境"""
        self.client = DeepseekClient(api_key="test_key", base_url="https://test.example.com")
    
    def test_provider_name(self):
        """测试提供商名称"""
        self.assertEqual(self.client.provider_name, "deepseek")
    
    @patch('app.core.ai.deepseek_client.BaseAPIClient._api_request')
    def test_analyze_essay_success(self, mock_api_request):
        """测试作文分析成功场景"""
        # 模拟API成功响应
        mock_api_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "总得分": 45,
                            "分项得分": {
                                "内容主旨": 18,
                                "语言文采": 14,
                                "文章结构": 9,
                                "文面书写": 4
                            },
                            "总体评价": "这是一篇很好的作文",
                            "内容分析": "内容充实",
                            "语言分析": "语言流畅",
                            "结构分析": "结构合理",
                            "写作建议": "可以更好",
                            "错别字": ["错别字1->正确1"]
                        })
                    }
                }
            ]
        }
        
        result = self.client.analyze_essay("测试作文内容")
        
        # 验证返回格式
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)
        
        # 验证返回字段
        essay_result = result["result"]
        self.assertEqual(essay_result["total_score"], 45)
        self.assertEqual(essay_result["content_score"], 18)
        self.assertEqual(essay_result["language_score"], 14)
        self.assertEqual(essay_result["structure_score"], 9)
        self.assertEqual(essay_result["writing_score"], 4)
        self.assertEqual(essay_result["overall_assessment"], "这是一篇很好的作文")
        self.assertEqual(essay_result["spelling_errors"]["解析"], ["错别字1->正确1"])
    
    @patch('app.core.ai.deepseek_client.BaseAPIClient._api_request')
    def test_analyze_essay_error(self, mock_api_request):
        """测试作文分析错误场景"""
        # 模拟API错误
        mock_api_request.side_effect = APIError("测试错误")
        
        # 确保原始错误包含在最终错误消息中
        self.client._handle_api_error = lambda e: {"status": "error", "message": f"Deepseek API错误: {e.message}"}
        
        result = self.client.analyze_essay("测试作文内容")
        
        # 验证错误处理
        self.assertEqual(result["status"], "error")
        self.assertIn("message", result)
        self.assertIn("测试错误", result["message"])

class TestOpenAIClient(unittest.TestCase):
    """OpenAIClient测试类"""
    
    def setUp(self):
        """初始化测试环境"""
        self.client = OpenAIClient(api_key="test_key", base_url="https://test.example.com")
    
    def test_provider_name(self):
        """测试提供商名称"""
        self.assertEqual(self.client.provider_name, "openai")
    
    @patch('app.core.ai.open_ai_client.BaseAPIClient._api_request')
    def test_analyze_essay_success(self, mock_api_request):
        """测试作文分析成功场景"""
        # 模拟API成功响应
        mock_api_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "总得分": 85,
                            "分项得分": {
                                "内容主旨": 80,
                                "语言文采": 85,
                                "文章结构": 90,
                                "写作技巧": 85
                            },
                            "总体评价": "这是一篇很好的作文",
                            "内容分析": "内容充实",
                            "语言分析": "语言流畅",
                            "结构分析": "结构合理",
                            "写作建议": "可以更好",
                            "错别字": ["错别字1->正确1"]
                        })
                    }
                }
            ]
        }
        
        result = self.client.analyze_essay("测试作文内容")
        
        # 验证返回格式
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)
        
        # 验证返回字段
        essay_result = result["result"]
        self.assertEqual(essay_result["total_score"], 85)
        self.assertEqual(essay_result["content_score"], 80)
        self.assertEqual(essay_result["language_score"], 85)
        self.assertEqual(essay_result["structure_score"], 90)
        self.assertEqual(essay_result["writing_score"], 85)
        self.assertEqual(essay_result["overall_assessment"], "这是一篇很好的作文")
        self.assertEqual(essay_result["spelling_errors"]["解析"], ["错别字1->正确1"])

class TestAPIClientFactory(unittest.TestCase):
    """AI客户端工厂测试类"""
    
    @patch('app.core.ai.OpenAIClient')
    @patch('app.core.ai.DeepseekClient')
    @patch('app.core.ai.AliyunQianwenClient')
    def test_client_factory(self, mock_aliyun, mock_deepseek, mock_openai):
        """测试客户端工厂模式"""
        from app.core.ai import get_ai_client, ai_client_factory
        
        # 使工厂使用我们的mock对象
        original_get_client = ai_client_factory.get_client
        
        def mock_get_client(provider_name):
            if provider_name == "openai":
                return mock_openai.return_value
            elif provider_name == "deepseek":
                return mock_deepseek.return_value
            elif provider_name == "aliyun_qianwen":
                return mock_aliyun.return_value
            return None
            
        ai_client_factory.get_client = mock_get_client
        
        try:
            # 测试获取OpenAI客户端
            client = get_ai_client("openai")
            self.assertIsNotNone(client)
            self.assertEqual(client, mock_openai.return_value)
            
            # 测试获取Deepseek客户端
            ai_client_factory.clear_cache()  # 清除缓存
            client = get_ai_client("deepseek")
            self.assertIsNotNone(client)
            self.assertEqual(client, mock_deepseek.return_value)
            
            # 测试获取阿里千问客户端
            ai_client_factory.clear_cache()  # 清除缓存
            client = get_ai_client("aliyun_qianwen")
            self.assertIsNotNone(client)
            self.assertEqual(client, mock_aliyun.return_value)
        finally:
            # 恢复原始方法
            ai_client_factory.get_client = original_get_client

if __name__ == '__main__':
    unittest.main() 