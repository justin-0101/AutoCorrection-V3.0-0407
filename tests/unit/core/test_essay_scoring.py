"""
作文评分功能单元测试
测试AI批改服务的功能
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os

from app.core.correction.ai_corrector import AICorrectionService
from app.core.ai import AIClientFactory
from app.core.services import container

class TestAICorrectionService(unittest.TestCase):
    """测试AI批改服务"""

    def setUp(self):
        """测试前准备"""
        # 准备测试前的环境
        container.clear()  # 使用clear方法替代直接操作_services
        self.mock_client = MagicMock()
        self.mock_factory = MagicMock()
        self.mock_factory.get_client.return_value = self.mock_client
        container.register("ai_client_factory", self.mock_factory)
        
        # 创建服务实例
        self.correction_service = AICorrectionService()
    
    def test_initialization(self):
        """测试服务初始化"""
        # 验证工厂方法被调用
        self.mock_factory.get_client.assert_called_once()
        self.assertEqual(self.correction_service.client, self.mock_client)
    
    def test_correct_essay_success(self):
        """测试成功的作文批改"""
        # 准备模拟数据
        mock_result = {
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
        
        # 配置模拟客户端的返回值
        self.mock_client.analyze_essay.return_value = mock_result
        
        # 调用功能并验证结果
        result = self.correction_service.correct_essay("这是一篇测试作文")
        
        # 验证期望结果
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"]["total_score"], 85)
        self.mock_client.analyze_essay.assert_called_once_with("这是一篇测试作文")
    
    def test_correct_essay_api_error(self):
        """测试API错误情况"""
        # 准备错误响应
        error_result = {
            "status": "error",
            "message": "API请求失败"
        }
        
        # 配置模拟客户端返回错误
        self.mock_client.analyze_essay.return_value = error_result
        
        # 调用功能
        result = self.correction_service.correct_essay("这是一篇测试作文")
        
        # 验证结果
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "API请求失败")
    
    def test_correct_essay_exception(self):
        """测试异常情况处理"""
        # 配置模拟客户端抛出异常
        self.mock_client.analyze_essay.side_effect = Exception("测试异常")
        
        # 调用功能
        result = self.correction_service.correct_essay("这是一篇测试作文")
        
        # 验证错误处理
        self.assertEqual(result["status"], "error")
        self.assertIn("测试异常", result["message"])
    
    def test_mock_result_generation(self):
        """测试模拟结果生成"""
        # 调用模拟结果生成方法
        mock_result = self.correction_service._generate_mock_result("这是一篇测试作文，内容不重要，主要测试长度影响分数")
        
        # 验证结果格式
        self.assertEqual(mock_result["status"], "success")
        self.assertIn("result", mock_result)
        self.assertIn("total_score", mock_result["result"])
        self.assertIn("content_score", mock_result["result"])
        self.assertIn("language_score", mock_result["result"])
        self.assertIn("structure_score", mock_result["result"])
        self.assertIn("writing_score", mock_result["result"])
        self.assertIn("overall_assessment", mock_result["result"])
        
        # 验证分数计算逻辑
        content = "短文本"
        short_result = self.correction_service._generate_mock_result(content)
        
        content = "这是一篇较长的文本，包含更多的内容，应该会得到不同的分数" * 5
        long_result = self.correction_service._generate_mock_result(content)
        
        # 验证不同长度文本生成不同分数
        self.assertNotEqual(short_result["result"]["total_score"], long_result["result"]["total_score"])


class TestEssayScoringIntegration(unittest.TestCase):
    """测试作文评分的集成功能"""
    
    def setUp(self):
        """设置测试环境"""
        # 确保在每个测试前清除容器
        container.clear()
    
    @patch('app.core.ai.open_ai_client.OpenAIClient.analyze_essay')
    def test_scoring_with_openai(self, mock_analyze):
        """测试使用OpenAI进行评分"""
        # 准备测试数据
        mock_response = {
            "status": "success",
            "result": {
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
            }
        }
        
        # 设置模拟返回值
        mock_analyze.return_value = mock_response
        
        # 设置环境
        with patch.dict('os.environ', {'AI_SERVICE': 'openai', 'OPENAI_API_KEY': 'test_key'}):
            # 注册AI客户端工厂
            container.register("ai_client_factory", AIClientFactory())
            
            # 创建服务并调用
            service = AICorrectionService()
            result = service.correct_essay("这是一篇测试作文")
            
            # 验证结果
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["result"]["total_score"], 88)
            mock_analyze.assert_called_once()
    
    @patch('app.core.ai.deepseek_client.DeepseekClient.analyze_essay')
    def test_scoring_with_deepseek(self, mock_analyze):
        """测试使用Deepseek进行评分"""
        # 准备测试数据
        mock_response = {
            "status": "success",
            "result": {
                "total_score": 92,
                "content_score": 90,
                "language_score": 94,
                "structure_score": 92,
                "writing_score": 92,
                "overall_assessment": "这是一篇优秀的作文",
                "content_analysis": "内容丰富、观点深刻",
                "language_analysis": "语言流畅，词汇丰富",
                "structure_analysis": "结构清晰，条理分明",
                "writing_analysis": "书写工整",
                "improvement_suggestions": "保持这种水平",
                "spelling_errors": {"错别字": []}
            }
        }
        
        # 设置模拟返回值
        mock_analyze.return_value = mock_response
        
        # 设置环境
        with patch.dict('os.environ', {'AI_SERVICE': 'deepseek', 'DEEPSEEK_API_KEY': 'test_key'}):
            # 注册AI客户端工厂
            container.register("ai_client_factory", AIClientFactory())
            
            # 创建服务并调用
            service = AICorrectionService()
            result = service.correct_essay("这是一篇测试作文")
            
            # 验证结果
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["result"]["total_score"], 92)
            mock_analyze.assert_called_once()

if __name__ == '__main__':
    unittest.main() 