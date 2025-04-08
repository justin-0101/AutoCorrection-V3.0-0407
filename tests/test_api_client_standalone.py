#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API客户端单元测试 - 独立版本
测试API客户端的基本功能
"""

import unittest
import json
from unittest.mock import patch, MagicMock

# 定义一个简单的基础API客户端，模拟我们实现的BaseAPIClient
class MockBaseAPIClient:
    """
    模拟基础API客户端
    """
    
    REQUIRED_RESULT_FIELDS = [
        'total_score', 'content_score', 'language_score', 
        'structure_score', 'writing_score', 'overall_assessment'
    ]
    
    def __init__(self, api_key=None, base_url=None, verify_ssl=True):
        self.api_key = api_key
        self.base_url = base_url
        self.verify_ssl = verify_ssl
    
    def _validate_config(self):
        """验证配置是否完整"""
        if not self.api_key:
            return False, "缺少API密钥"
        if not self.base_url:
            return False, "缺少基础URL"
        return True, ""
    
    def _api_request(self, url, headers, data, timeout=30):
        """API请求方法"""
        # 这个方法在实际使用时会被模拟替换
        pass
    
    def validate_response(self, response_data):
        """验证响应数据是否符合要求"""
        if not isinstance(response_data, dict):
            return False, ["响应格式不是JSON对象"]
        
        missing_fields = []
        for field in self.REQUIRED_RESULT_FIELDS:
            if field not in response_data:
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    def format_response(self, result_data):
        """格式化响应结果"""
        # 检查是否有缺失字段
        valid, missing_fields = self.validate_response(result_data)
        
        # 如果有缺失字段，使用默认值填充
        if not valid:
            for field in missing_fields:
                result_data[field] = "未提供" if field.endswith('assessment') else 0
        
        # 组装标准响应格式
        return {
            "status": "success",
            "result": result_data
        }
    
    def analyze_essay(self, essay_content):
        """分析作文内容"""
        # 这个方法将在子类中实现
        pass


# 定义模拟的OpenAI客户端实现
class MockOpenAIClient(MockBaseAPIClient):
    """
    模拟OpenAI客户端
    """
    
    def __init__(self, api_key=None, base_url=None, model="gpt-3.5-turbo", verify_ssl=True):
        super().__init__(api_key, base_url, verify_ssl)
        self.model = model
    
    def analyze_essay(self, essay_content):
        """分析作文内容"""
        try:
            # 模拟API请求过程
            # 实际实现时会使用self._api_request方法
            # 这里直接返回模拟数据
            
            # 检查配置
            valid_config, error_message = self._validate_config()
            if not valid_config:
                return {"status": "error", "message": error_message}
            
            # 模拟响应数据
            result = {
                "total_score": 85,
                "content_score": 80,
                "language_score": 90,
                "structure_score": 85,
                "writing_score": 85,
                "overall_assessment": "这是一篇很好的作文"
            }
            
            # 返回标准格式响应
            return self.format_response(result)
        
        except Exception as e:
            # 异常处理
            return {"status": "error", "message": str(e)}


# 测试基础API客户端
class TestBaseAPIClient(unittest.TestCase):
    """测试基础API客户端"""
    
    def setUp(self):
        """测试前准备"""
        self.client = MockBaseAPIClient(api_key="test_key", base_url="https://api.example.com")
    
    def test_required_fields(self):
        """测试必需字段定义"""
        # 验证必需字段列表
        self.assertIn('total_score', self.client.REQUIRED_RESULT_FIELDS)
        self.assertIn('content_score', self.client.REQUIRED_RESULT_FIELDS)
        self.assertIn('language_score', self.client.REQUIRED_RESULT_FIELDS)
        self.assertIn('structure_score', self.client.REQUIRED_RESULT_FIELDS)
        self.assertIn('writing_score', self.client.REQUIRED_RESULT_FIELDS)
        self.assertIn('overall_assessment', self.client.REQUIRED_RESULT_FIELDS)
    
    def test_validate_response(self):
        """测试响应验证方法"""
        # 测试完整响应
        complete_response = {
            'total_score': 85,
            'content_score': 80,
            'language_score': 90,
            'structure_score': 85,
            'writing_score': 85,
            'overall_assessment': "这是一篇很好的作文"
        }
        valid, missing = self.client.validate_response(complete_response)
        self.assertTrue(valid)
        self.assertEqual(len(missing), 0)
        
        # 测试缺失字段
        incomplete_response = {
            'total_score': 85,
            'content_score': 80
        }
        valid, missing = self.client.validate_response(incomplete_response)
        self.assertFalse(valid)
        self.assertIn('language_score', missing)
        self.assertIn('structure_score', missing)
        self.assertIn('writing_score', missing)
        self.assertIn('overall_assessment', missing)
        
        # 测试空响应
        empty_response = {}
        valid, missing = self.client.validate_response(empty_response)
        self.assertFalse(valid)
        self.assertEqual(len(missing), len(self.client.REQUIRED_RESULT_FIELDS))
    
    def test_format_response(self):
        """测试响应格式化方法"""
        # 测试完整响应
        complete_data = {
            'total_score': 85,
            'content_score': 80,
            'language_score': 90,
            'structure_score': 85,
            'writing_score': 85,
            'overall_assessment': "这是一篇很好的作文"
        }
        response = self.client.format_response(complete_data)
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"], complete_data)
        
        # 测试不完整响应的自动填充
        incomplete_data = {
            'total_score': 85,
            'content_score': 80
        }
        response = self.client.format_response(incomplete_data)
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"]["total_score"], 85)
        self.assertEqual(response["result"]["content_score"], 80)
        self.assertEqual(response["result"]["language_score"], 0)  # 自动填充数值
        self.assertEqual(response["result"]["overall_assessment"], "未提供")  # 自动填充字符串


# 测试OpenAI客户端
class TestOpenAIClient(unittest.TestCase):
    """测试OpenAI客户端"""
    
    def setUp(self):
        """测试前准备"""
        self.client = MockOpenAIClient(
            api_key="test_key",
            base_url="https://api.openai.com/v1",
            model="gpt-3.5-turbo"
        )
    
    def test_analyze_essay(self):
        """测试作文分析方法"""
        # 调用分析方法
        response = self.client.analyze_essay("这是一篇测试作文，用于单元测试。")
        
        # 验证响应格式
        self.assertEqual(response["status"], "success")
        self.assertIn("result", response)
        
        # 验证分数字段
        result = response["result"]
        self.assertIn("total_score", result)
        self.assertIn("content_score", result)
        self.assertIn("language_score", result)
        self.assertIn("structure_score", result)
        self.assertIn("writing_score", result)
        self.assertIn("overall_assessment", result)
    
    def test_missing_config(self):
        """测试缺失配置的处理"""
        # 创建缺少API密钥的客户端
        client_no_key = MockOpenAIClient(base_url="https://api.openai.com/v1")
        response = client_no_key.analyze_essay("测试文本")
        self.assertEqual(response["status"], "error")
        self.assertIn("缺少API密钥", response["message"])
        
        # 创建缺少Base URL的客户端
        client_no_url = MockOpenAIClient(api_key="test_key")
        response = client_no_url.analyze_essay("测试文本")
        self.assertEqual(response["status"], "error")
        self.assertIn("缺少基础URL", response["message"])


if __name__ == "__main__":
    unittest.main() 