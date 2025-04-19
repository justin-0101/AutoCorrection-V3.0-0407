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
import asyncio
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
            logger.info(f"[AICorrectionService] 开始AI批改，内容长度: {len(content)}，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 记录客户端信息
            client_type = type(self.ai_client).__name__
            client_methods = dir(self.ai_client)
            available_methods = [m for m in client_methods if not m.startswith('_') and callable(getattr(self.ai_client, m))]
            
            logger.info(f"[AICorrectionService] 使用的AI客户端类型: {client_type}")
            logger.info(f"[AICorrectionService] 客户端可用方法: {available_methods}")
            
            # 调用AI客户端进行批改
            logger.info(f"[AICorrectionService] 调用correct_essay方法进行批改")
            result = self.ai_client.correct_essay(content)
            
            # 验证结果有效性
            if self._is_valid_result(result):
                logger.info(f"AI批改成功，essay_id={essay_id}")
                return result
            else:
                logger.warning(f"AI返回无效结果，essay_id={essay_id}，结果: {result}")
                # 如果结果无效，返回模拟结果
                mock_result = self._generate_mock_result(content)
                mock_result["result"]["ai_error"] = "AI返回无效结果结构"
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
    
    async def correct_essay_async(self, content: str, essay_id: Optional[str] = None) -> Dict[str, Any]:
        """
        异步分析作文内容并返回批改结果
        
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
            logger.info(f"[AICorrectionService] 开始异步AI批改，内容长度: {len(content)}，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 记录客户端信息
            client_type = type(self.ai_client).__name__
            client_methods = dir(self.ai_client)
            available_methods = [m for m in client_methods if not m.startswith('_') and callable(getattr(self.ai_client, m))]
            
            logger.info(f"[AICorrectionService] 使用的AI客户端类型: {client_type}")
            logger.info(f"[AICorrectionService] 客户端可用方法: {available_methods}")
            
            # 检查客户端是否支持异步方法
            if hasattr(self.ai_client, 'correct_essay_async') and callable(getattr(self.ai_client, 'correct_essay_async')):
                # 调用AI客户端进行异步批改
                logger.info(f"[AICorrectionService] 调用correct_essay_async方法进行异步批改")
                result = await self.ai_client.correct_essay_async(content)
            else:
                # 如果客户端不支持异步方法，使用同步方法并包装为异步
                logger.info(f"[AICorrectionService] 客户端不支持异步方法，使用同步方法包装为异步")
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.ai_client.correct_essay(content)
                )
            
            # 验证结果有效性
            if self._is_valid_result(result):
                logger.info(f"异步AI批改成功，essay_id={essay_id}")
                return result
            else:
                logger.warning(f"异步AI返回无效结果，essay_id={essay_id}，结果: {result}")
                # 如果结果无效，返回模拟结果
                mock_result = self._generate_mock_result(content)
                mock_result["result"]["ai_error"] = "异步AI返回无效结果结构"
                mock_result["result"]["is_mock"] = True
                return mock_result
                
        except Exception as e:
            logger.error(f"异步AI批改服务发生错误: {str(e)}")
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
            
        # 检查状态
        if isinstance(result, dict) and result.get("status") == "error":
            return False
            
        # 检查是否有结果字段
        if isinstance(result, dict) and "result" not in result:
            return False
            
        # 获取结果部分
        result_data = result.get("result", {}) if isinstance(result, dict) else result
            
        # 检查必要字段
        required_fields = ["总得分", "分项得分", "总体评价"]
        for field in required_fields:
            if field not in result_data:
                return False
                
        # 检查分数是否在合理范围内
        if not isinstance(result_data.get("总得分"), (int, float)) or result_data.get("总得分") < 0 or result_data.get("总得分") > 100:
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