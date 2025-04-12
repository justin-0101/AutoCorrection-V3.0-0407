#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI批改服务模块
用于实现AI批改流程
"""

import json
import random
import logging
import traceback
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class AICorrectionService:
    """AI批改服务"""
    
    def __init__(self, ai_service: str = "deepseek", debug_mode: bool = False):
        """
        初始化AI批改服务
        
        Args:
            ai_service: AI服务名称，默认为"deepseek"
            debug_mode: 是否启用调试模式
        """
        self.ai_service = ai_service
        self.debug_mode = debug_mode
        
        # 初始化AI客户端
        try:
            # 尝试直接导入DeepseekClient
            from app.core.ai.deepseek_client import DeepseekClient
            api_key = os.environ.get('DEEPSEEK_API_KEY', '')
            base_url = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
            model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
            
            if not api_key:
                logger.warning("未配置DeepSeek API密钥，将使用调试模式")
                self.debug_mode = True
            else:
                self.ai_client = DeepseekClient(api_key=api_key, base_url=base_url, model=model)
                logger.info(f"已创建DeepseekClient实例，模型: {model}")
        except Exception as e:
            logger.error(f"创建AI客户端失败: {str(e)}")
            logger.error(traceback.format_exc())
            self.debug_mode = True  # 失败时强制启用调试模式
            
        logger.info(f"初始化AI批改服务，使用{ai_service}引擎，调试模式: {self.debug_mode}")
    
    def correct_essay(self, content: str, essay_id: Optional[str] = None) -> Dict[str, Any]:
        """
        分析作文内容并返回批改结果
        
        Args:
            content: 作文内容
            essay_id: 作文ID（可选，用于跟踪）
            
        Returns:
            Dict: 批改结果
        """
        try:
            # 如果启用了调试模式，使用模拟数据
            if self.debug_mode:
                logger.info(f"调试模式：生成模拟批改结果，essay_id={essay_id}")
                return self._generate_mock_result(content)
            
            # 记录正在处理的作文
            essay_info = f"ID: {essay_id}" if essay_id else f"长度: {len(content)}"
            logger.info(f"AI批改开始处理作文，{essay_info}")
            
            # 尝试调用AI客户端进行批改
            max_retries = 2
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.warning(f"AI批改重试 {attempt}/{max_retries}，essay_id={essay_id}")
                    
                    # 调用AI客户端进行批改
                    result = self.ai_client.correct_essay(content)
                    
                    # 验证结果有效性
                    if self._is_valid_result(result):
                        logger.info(f"AI批改成功，essay_id={essay_id}")
                        return {
                            "status": "success",
                            "result": result
                        }
                    else:
                        logger.warning(f"AI返回无效结果，essay_id={essay_id}，结果: {result}")
                        last_error = "AI返回无效结果结构"
                        # 继续重试
                        
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"AI批改尝试 {attempt+1}/{max_retries+1} 失败: {last_error}")
                    logger.error(traceback.format_exc())
                    # 继续重试
            
            # 所有重试都失败，返回模拟结果
            logger.warning(f"AI批改失败后回退到模拟结果，essay_id={essay_id}，错误: {last_error}")
            mock_result = self._generate_mock_result(content)
            mock_result["result"]["ai_error"] = last_error
            mock_result["result"]["is_mock"] = True
            return mock_result
            
        except Exception as e:
            logger.error(f"AI批改服务发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 出错时返回模拟结果
            mock_result = self._generate_mock_result(content)
            mock_result["result"]["ai_error"] = str(e)
            mock_result["result"]["is_mock"] = True
            return mock_result
    
    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        """
        验证批改结果是否有效
        
        Args:
            result: 批改结果
            
        Returns:
            bool: 是否有效
        """
        # 检查是否有错误信息
        if isinstance(result, dict) and "error" in result:
            return False
            
        # 检查必要字段
        required_fields = ["总得分", "分项得分", "总体评价"]
        for field in required_fields:
            if field not in result:
                return False
                
        # 检查分数是否在合理范围内
        if not isinstance(result.get("总得分"), (int, float)) or result.get("总得分") < 0 or result.get("总得分") > 100:
            return False
            
        return True
    
    def _generate_mock_result(self, content: str) -> Dict[str, Any]:
        """
        生成模拟的批改结果（用于调试或API不可用时）
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 模拟的批改结果
        """
        # 基于内容长度生成分数
        content_length = len(content)
        base_score = 30  # 基础分数
        
        # 内容越长，分数越高，最高50分
        length_factor = min(content_length / 1000, 1.0)  # 长度因子，最高1.0
        total_score = min(base_score + int(length_factor * 20), 50)
        
        # 随机波动
        total_score = max(min(total_score + random.randint(-5, 5), 50), 30)
        
        # 分项得分
        content_score = int(total_score * 0.35)
        language_score = int(total_score * 0.25)
        structure_score = int(total_score * 0.15)
        writing_score = int(total_score * 0.10)
        
        # 找出一些可能的拼写错误（简单模拟）
        words = content.split()
        potential_errors = []
        for i in range(min(3, len(words))):
            if len(words) > 0:
                index = random.randint(0, len(words) - 1)
                if len(words[index]) > 3:
                    wrong = words[index]
                    correct = wrong  # 在真实场景中这里应该是修正的单词
                    potential_errors.append(f"{wrong}->{correct}")
        
        return {
            "status": "success",
            "result": {
                "总得分": total_score,
                "分项得分": {
                    "内容主旨": content_score,
                    "语言文采": language_score,
                    "文章结构": structure_score,
                    "文面书写": writing_score
                },
                "总体评价": "这是一份自动生成的评价。作文内容结构合理，但需要注意错别字和语言表达方面的问题。建议多阅读优秀范文，提高语言表达能力。",
                "内容分析": "文章主题明确，有一定的思想深度。能够围绕主题展开论述，但论据的说服力和创新性有待提高。",
                "语言分析": "语言表达基本流畅，用词基本准确，但部分句式单一，缺乏变化。建议增加修辞手法的运用。",
                "结构分析": "文章结构比较清晰，但过渡不够自然，段落之间的连贯性有待加强。",
                "写作建议": "建议增加阅读量，积累优美词句；注意文章结构的严谨性；多角度思考问题，增强论证的说服力。",
                "错别字": potential_errors,
                "is_mock": True,  # 标记为模拟结果
                "mock_reason": "调试模式或API调用失败"
            }
        } 