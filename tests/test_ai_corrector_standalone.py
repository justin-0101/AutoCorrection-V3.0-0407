#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI批改服务单元测试 - 独立版本
测试AI批改服务的基本功能
"""

import unittest
import json
from unittest.mock import patch, MagicMock, PropertyMock

# 定义一个模拟的AI客户端
class MockAIClient:
    """
    模拟AI客户端
    用于测试AI批改服务
    """
    
    def __init__(self, api_key="test_key", base_url="https://api.example.com"):
        """初始化AI客户端"""
        self.api_key = api_key
        self.base_url = base_url
    
    def analyze_essay(self, essay_content):
        """
        分析作文内容
        
        Args:
            essay_content: 作文内容
            
        Returns:
            dict: 分析结果
        """
        # 模拟返回结果，而非实际调用API
        mock_result = {
            "status": "success",
            "result": {
                "total_score": 85,
                "content_score": 80,
                "language_score": 90,
                "structure_score": 85,
                "writing_score": 85,
                "overall_assessment": "这是一篇很好的作文",
                "content_assessment": "内容丰富，观点清晰",
                "language_assessment": "语言流畅，用词准确",
                "structure_assessment": "结构完整，逻辑清晰",
                "writing_assessment": "书写规范，格式正确",
                "suggestions": [
                    "可以增加更多具体例子",
                    "结论部分可以更加深入"
                ]
            }
        }
        
        return mock_result


# 模拟AI客户端工厂
class MockAIClientFactory:
    """
    模拟AI客户端工厂
    提供不同类型的AI客户端实例
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(MockAIClientFactory, cls).__new__(cls)
            cls._instance._clients = {}
        return cls._instance
    
    def get_client(self, provider_name):
        """
        获取指定类型的AI客户端
        
        Args:
            provider_name: 提供者名称，如'openai', 'deepseek'等
            
        Returns:
            object: AI客户端实例
        """
        if provider_name in self._clients:
            return self._clients[provider_name]
        
        # 创建新客户端
        client = MockAIClient()
        
        # 缓存客户端
        self._clients[provider_name] = client
        
        return client


# 模拟AI批改服务
class MockAICorrectionService:
    """
    模拟AI批改服务
    使用AI客户端工厂获取客户端并分析作文
    """
    
    def __init__(self):
        """初始化AI批改服务"""
        self.ai_service = "deepseek"  # 默认使用deepseek
        self.client_factory = MockAIClientFactory()
        self.client = self.client_factory.get_client(self.ai_service)
    
    def set_ai_service(self, service_name):
        """
        设置AI服务类型
        
        Args:
            service_name: 服务名称
        """
        self.ai_service = service_name
        self.client = self.client_factory.get_client(service_name)
    
    def correct_essay(self, essay_content, essay_title=None):
        """
        批改作文
        
        Args:
            essay_content: 作文内容
            essay_title: 作文标题
            
        Returns:
            dict: 批改结果
        """
        if not essay_content:
            return {
                "status": "error",
                "message": "作文内容不能为空"
            }
            
        try:
            # 调用AI客户端分析作文
            response = self.client.analyze_essay(essay_content)
            
            # 处理成功的情况
            if response.get("status") == "success":
                # 获取分析结果
                result = response.get("result", {})
                
                # 检查结果格式
                if not isinstance(result, dict):
                    return {
                        "status": "error",
                        "message": "AI分析结果格式错误"
                    }
                
                # 计算平均分
                total_score = result.get("total_score", 0)
                
                # 添加元数据
                metadata = {
                    "title": essay_title or "未命名作文",
                    "word_count": len(essay_content),
                    "ai_service": self.ai_service
                }
                
                # 构建标准化的结果格式
                correction_result = {
                    "status": "success",
                    "metadata": metadata,
                    "scores": {
                        "total": total_score,
                        "content": result.get("content_score", 0),
                        "language": result.get("language_score", 0),
                        "structure": result.get("structure_score", 0),
                        "writing": result.get("writing_score", 0)
                    },
                    "assessments": {
                        "overall": result.get("overall_assessment", ""),
                        "content": result.get("content_assessment", ""),
                        "language": result.get("language_assessment", ""),
                        "structure": result.get("structure_assessment", ""),
                        "writing": result.get("writing_assessment", "")
                    },
                    "suggestions": result.get("suggestions", [])
                }
                
                return correction_result
            else:
                # 处理错误情况
                return {
                    "status": "error",
                    "message": response.get("message", "AI服务响应错误")
                }
                
        except Exception as e:
            # 处理异常
            return {
                "status": "error",
                "message": f"批改过程发生错误: {str(e)}"
            }


# 测试AI批改服务
class TestAICorrectionService(unittest.TestCase):
    """测试AI批改服务"""
    
    def setUp(self):
        """测试前准备"""
        self.corrector = MockAICorrectionService()
        
        # 创建测试用的作文内容
        self.test_essay = """
        绿色环保
        
        随着工业化的快速发展，环境污染日益严重。保护环境已成为全球关注的焦点。
        绿色环保是一种生活方式，从小事做起，节约资源，减少浪费。
        我们应该减少使用塑料袋，多使用环保袋；节约用水用电，不随地乱扔垃圾。
        绿色环保需要全社会共同努力，政府应该加强环保法规，企业应该采用清洁生产技术。
        如果每个人都能从自己做起，我们的地球家园将会更加美好。
        """
    
    def test_correct_essay_success(self):
        """测试成功批改作文"""
        # 调用批改方法
        result = self.corrector.correct_essay(self.test_essay, "绿色环保")
        
        # 验证结果格式
        self.assertEqual(result["status"], "success")
        self.assertIn("metadata", result)
        self.assertIn("scores", result)
        self.assertIn("assessments", result)
        self.assertIn("suggestions", result)
        
        # 验证各个分数字段
        self.assertIn("total", result["scores"])
        self.assertIn("content", result["scores"])
        self.assertIn("language", result["scores"])
        self.assertIn("structure", result["scores"])
        self.assertIn("writing", result["scores"])
        
        # 验证评价字段
        self.assertIn("overall", result["assessments"])
        self.assertIn("content", result["assessments"])
        self.assertIn("language", result["assessments"])
        self.assertIn("structure", result["assessments"])
        self.assertIn("writing", result["assessments"])
        
        # 验证元数据
        self.assertEqual(result["metadata"]["title"], "绿色环保")
        self.assertEqual(result["metadata"]["word_count"], len(self.test_essay))
        self.assertEqual(result["metadata"]["ai_service"], "deepseek")
    
    def test_empty_essay(self):
        """测试空作文的处理"""
        # 调用批改方法，传入空内容
        result = self.corrector.correct_essay("")
        
        # 验证错误结果
        self.assertEqual(result["status"], "error")
        self.assertIn("作文内容不能为空", result["message"])
    
    def test_change_ai_service(self):
        """测试更换AI服务"""
        # 更换到OpenAI服务
        self.corrector.set_ai_service("openai")
        
        # 调用批改方法
        result = self.corrector.correct_essay(self.test_essay)
        
        # 验证服务已更换
        self.assertEqual(result["metadata"]["ai_service"], "openai")
    
    @patch.object(MockAIClient, 'analyze_essay')
    def test_ai_client_error(self, mock_analyze):
        """测试AI客户端错误的处理"""
        # 模拟AI客户端返回错误
        mock_analyze.return_value = {
            "status": "error",
            "message": "API请求失败"
        }
        
        # 调用批改方法
        result = self.corrector.correct_essay(self.test_essay)
        
        # 验证错误传递
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "API请求失败")
        
        # 验证方法被正确调用
        mock_analyze.assert_called_once_with(self.test_essay)
    
    @patch.object(MockAIClient, 'analyze_essay')
    def test_unexpected_exception(self, mock_analyze):
        """测试意外异常的处理"""
        # 模拟AI客户端抛出异常
        mock_analyze.side_effect = Exception("意外错误")
        
        # 调用批改方法
        result = self.corrector.correct_essay(self.test_essay)
        
        # 验证异常被捕获并返回错误信息
        self.assertEqual(result["status"], "error")
        self.assertIn("批改过程发生错误", result["message"])
        self.assertIn("意外错误", result["message"])


if __name__ == "__main__":
    unittest.main() 