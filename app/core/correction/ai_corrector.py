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

from app.core.services.container import container, ServiceScope
from app.core.correction.correction_logger import correction_logger

logger = logging.getLogger(__name__)

class AICorrectionService:
    """AI批改服务"""
    
    def __init__(self):
        """初始化AI批改服务"""
        self.ai_service = os.environ.get("AI_SERVICE", "deepseek")  # 默认使用deepseek
        
        # 使用服务容器获取AI客户端工厂
        ai_factory = container.get("ai_client_factory")
        if ai_factory is None:
            logger.warning("未能从服务容器获取AI客户端工厂，创建新实例")
            from app.core.ai import ai_client_factory
            ai_factory = ai_client_factory
        
        # 使用工厂获取客户端
        self.client = ai_factory.get_client(self.ai_service)
        logger.info(f"初始化AI批改服务，使用: {self.ai_service}")
    
    @correction_logger.monitor_correction
    def correct_essay(self, content, essay_id: str = None):
        """
        使用AI对作文进行批改
        
        Args:
            content: 作文内容
            essay_id: 作文ID，用于日志追踪
            
        Returns:
            dict: 批改结果
        """
        try:
            # 使用选定的AI客户端进行分析
            result = self.client.correct_essay(content)
            
            if result["status"] == "success":
                return result
            else:
                return {
                    "status": "error",
                    "message": result.get('message', '未知错误')
                }
        
        except Exception as e:
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