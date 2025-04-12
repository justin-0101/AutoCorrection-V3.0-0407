#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI批改服务
提供AI批改功能的接口
"""

import logging
import json
import traceback
import os
from datetime import datetime

from app.core.ai import AIClientFactory

logger = logging.getLogger(__name__)

class AICorrectionService:
    """AI批改服务"""
    
    def __init__(self):
        """初始化AI批改服务"""
        self.ai_service = os.environ.get("AI_SERVICE", "deepseek")  # 默认使用deepseek
        
        # 直接创建AI客户端工厂的实例
        self.ai_factory = AIClientFactory()
        
        # 使用工厂获取客户端
        self.client = self.ai_factory.get_client(self.ai_service)
        print(f"[AICorrectionService] 初始化AI批改服务，使用: {self.ai_service}")
        logger.info(f"[AICorrectionService] 初始化AI批改服务，使用: {self.ai_service}")
        
    def correct_essay(self, content):
        """
        使用AI对作文进行批改
        
        Args:
            content: 作文内容
            
        Returns:
            dict: 批改结果
        """
        print(f"[AICorrectionService] 开始AI批改，内容长度: {len(content)}，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[AICorrectionService] 开始AI批改，内容长度: {len(content)}")
        
        try:
            # 使用选定的AI客户端进行分析
            if not self.client:
                error_msg = f"AI客户端未初始化，服务: {self.ai_service}"
                print(f"[AICorrectionService] {error_msg}")
                logger.error(f"[AICorrectionService] {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg
                }
            
            # 记录客户端类型和可用方法
            client_type = type(self.client).__name__
            client_methods = [m for m in dir(self.client) if not m.startswith('_') and callable(getattr(self.client, m))]
            
            print(f"[AICorrectionService] 使用的AI客户端类型: {client_type}")
            print(f"[AICorrectionService] 客户端可用方法: {client_methods}")
            logger.info(f"[AICorrectionService] 使用的AI客户端类型: {client_type}")
            logger.info(f"[AICorrectionService] 客户端可用方法: {client_methods}")
            
            # 使用correct_essay方法进行批改
            print(f"[AICorrectionService] 调用correct_essay方法进行批改")
            logger.info(f"[AICorrectionService] 调用correct_essay方法进行批改")
            
            # 记录开始时间
            start_time = datetime.now()
            
            # 调用客户端的correct_essay方法
            result = self.client.correct_essay(content)
            
            # 计算总耗时
            elapsed_time = (datetime.now() - start_time).total_seconds()
            print(f"[AICorrectionService] 批改完成，总耗时: {elapsed_time:.2f}秒")
            logger.info(f"[AICorrectionService] 批改完成，总耗时: {elapsed_time:.2f}秒")
            
            if result["status"] == "success":
                total_score = result.get('result', {}).get('total_score', '未知')
                print(f"[AICorrectionService] AI批改完成，生成结果: {total_score}分")
                logger.info(f"[AICorrectionService] AI批改完成，生成结果: {total_score}分")
                return result
            else:
                error_msg = result.get('message', '未知错误')
                print(f"[AICorrectionService] AI批改失败: {error_msg}")
                logger.error(f"[AICorrectionService] AI批改失败: {error_msg}")
                return result
        
        except Exception as e:
            print(f"[AICorrectionService] AI批改过程中发生错误: {str(e)}")
            logger.error(f"[AICorrectionService] AI批改过程中发生错误: {str(e)}")
            logger.error(f"[AICorrectionService] 错误详情: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"AI批改失败: {str(e)}"
            }
    
    def _generate_mock_result(self, content):
        """生成模拟批改结果，用于测试"""
        word_count = len(content)
        score = min(95, max(70, 85 + (word_count % 10) - 5))
        
        return {
            "status": "success",
            "result": {
                "total_score": score,
                "content_score": min(100, score + 2),
                "language_score": min(100, score + 3),
                "structure_score": min(100, score - 1),
                "writing_score": min(100, score + 1),
                "overall_assessment": f"这是一篇内容充实、结构清晰的作文，总体评分为{score}分。",
                "content_analysis": "文章主题明确，论述有力，观点新颖。" if score > 85 else "文章内容尚可，但论述不够深入。",
                "language_analysis": "语言表达流畅，用词准确，句式多样。" if score > 80 else "语言表达基本流畅，但用词不够精准。",
                "structure_analysis": "文章结构合理，层次分明，过渡自然。" if score > 85 else "文章结构基本合理，但层次不够分明。",
                "writing_analysis": "字迹工整，标点符号使用正确，卷面整洁。",
                "improvement_suggestions": "建议进一步丰富论据，增强说服力。",
                "spelling_errors": {
                    "错别字": []
                }
            }
        } 