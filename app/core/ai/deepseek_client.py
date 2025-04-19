#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Deepseek AI客户端
用于与Deepseek API交互
"""

import os
import json
import logging
import traceback
import time
from typing import Dict, Any, List, Optional, Union
import re
import asyncio
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from datetime import datetime

from app.core.ai.api_client import BaseAPIClient, APIError
from app.core.ai.api_monitor import log_api_call, log_api_call_async, api_monitor
from config.ai_config import AI_CONFIG

# 导入OpenAI SDK (旧版本 0.28.0)
try:
    import openai
except ImportError:
    logging.error("未安装OpenAI SDK，请执行 pip install openai==0.28.0")

# 配置日志
logger = logging.getLogger(__name__)

class DeepseekClient(BaseAPIClient):
    """Deepseek AI客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, verify_ssl: bool = True):
        """
        初始化Deepseek客户端
        
        Args:
            api_key: Deepseek API密钥
            base_url: Deepseek API基础URL
            model: 使用的模型
            verify_ssl: 是否验证SSL证书
        """
        self.model = model or AI_CONFIG.get('MODEL', "deepseek-reasoner")
        super().__init__(api_key, base_url, verify_ssl)
        
        # 修正：正确处理API基础路径，确保包含/v1
        self.api_base = self.base_url.rstrip('/')
        if not self.api_base.endswith('/v1'):
            self.api_base = f"{self.api_base}/v1"
            
        # 保存原始URL用于日志记录
        self.original_base_url = self.base_url
        
        logger.info(f"DeepSeek API原始URL: {self.original_base_url}")
        logger.info(f"DeepSeek API修正URL: {self.api_base}")
        
        # 设置OpenAI全局配置
        openai.api_key = self.api_key
        openai.api_base = self.api_base
        
        # API调用配置
        self.api_config = {
            'timeout': 60,    # 超时时间（秒）
            'max_tokens': 8000,  # 增加token限制到8000
            'chunk_size': 4000,  # 增加分块大小
            'temperature': 0.7,
            'top_p': 0.95,
            'frequency_penalty': 0,
            'presence_penalty': 0
        }
        
        # 验证模型可用性
        VALID_MODELS = ["deepseek-reasoner", "deepseek-chat", "deepseek-coder"]
        if self.model not in VALID_MODELS:
            logger.warning(f"可能使用了未知的模型: {self.model}，建议使用: {', '.join(VALID_MODELS)}")
        
        logger.info(f"Deepseek客户端初始化完成，使用模型: {self.model}")
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return "deepseek"
    
    def _load_config_from_env(self):
        """从环境变量和配置加载配置"""
        # 先从AI_CONFIG加载
        self.api_key = self.api_key or AI_CONFIG.get('API_KEY', '')
        self.base_url = self.base_url or AI_CONFIG.get('BASE_URL', '')
        
        # 如果还是没有，从环境变量加载
        self.api_key = self.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = self.base_url or os.environ.get("DEEPSEEK_BASE_URL", "")
        
        # 只有在没有任何配置的情况下使用默认值
        # 根据官方文档，正确的默认URL是https://api.deepseek.com
        if not self.base_url:
            self.base_url = "https://api.deepseek.com"
            logger.info(f"使用默认DeepSeek API URL: {self.base_url}")
        
        # 从环境变量或配置加载模型
        config_model = AI_CONFIG.get('MODEL', "")
        env_model = os.environ.get("DEEPSEEK_MODEL", "")
        
        if not self.model:
            if config_model:
                logger.info(f"从配置中加载模型: {config_model}")
                self.model = config_model
            elif env_model:
                logger.info(f"从环境变量中加载模型: {env_model}")
                self.model = env_model
            else:
                logger.info(f"使用默认模型: deepseek-reasoner")
                self.model = "deepseek-reasoner"
        
        logger.info(f"DeepSeek API最终配置 - URL: {self.base_url}, 模型: {self.model}")
    
    def _clean_json(self, json_str: str) -> str:
        """
        清除JSON字符串中的控制字符和非法字符
        
        Args:
            json_str: 原始JSON字符串
            
        Returns:
            str: 清洗后的JSON字符串
        """
        # 移除控制字符和其他可能导致JSON解析错误的字符
        return re.sub(r'[\x00-\x1F\x7F]', '', json_str)

    def _clean_json_string(self, json_str: str) -> str:
        """
        清理JSON字符串，包括提取代码块中的JSON和去除无关字符
        
        Args:
            json_str: 原始JSON字符串
            
        Returns:
            str: 清洗后的JSON字符串
        """
        # 先尝试提取代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
        if json_match:
            logger.debug("从代码块中提取JSON")
            json_str = json_match.group(1)
        
        # 移除控制字符和其他可能导致JSON解析错误的字符
        json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
        
        # 尝试找到并截取第一个有效的JSON对象（从第一个{到匹配的最后一个}）
        try:
            start_idx = json_str.find('{')
            if start_idx >= 0:
                # 找到平衡的大括号对
                count = 0
                end_idx = -1
                for i in range(start_idx, len(json_str)):
                    if json_str[i] == '{':
                        count += 1
                    elif json_str[i] == '}':
                        count -= 1
                        if count == 0:
                            end_idx = i + 1
                            break
                
                if end_idx > start_idx:
                    json_str = json_str[start_idx:end_idx]
                    logger.debug(f"截取了有效的JSON对象: {json_str[:50]}...")
        except Exception as e:
            logger.warning(f"尝试截取JSON对象时出错: {str(e)}")
        
        return json_str

    def format_response(self, response: Dict) -> Dict[str, Any]:
        """
        格式化API响应结果
        
        Args:
            response: API响应
            
        Returns:
            Dict: 格式化后的结果
        """
        try:
            result = self._extract_result(response)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.error(f"格式化Deepseek响应时发生错误: {str(e)}")
            return {
                "status": "error",
                "message": f"格式化响应失败: {str(e)}"
            }
    
    def _extract_result(self, response):
        """
        从API响应中提取结果
        
        Args:
            response: API响应
            
        Returns:
            Dict: 提取的结果
        """
        content = ""
        try:
            # 处理Deepseek API的响应格式
            if isinstance(response, dict):
                if 'choices' in response and len(response['choices']) > 0:
                    choice = response['choices'][0]
                    if 'message' in choice:
                        # 检查是否有reasoning_content字段
                        if 'reasoning_content' in choice['message']:
                            raw_content = choice['message'].get('reasoning_content', '')
                            logger.debug(f"从reasoning_content字段获取内容，长度: {len(raw_content)}")
                        elif 'content' in choice['message']:
                            raw_content = choice['message'].get('content', '')
                            logger.debug(f"从content字段获取内容，长度: {len(raw_content)}")
                        else:
                            raw_content = ""
                            logger.debug("message中未找到content或reasoning_content字段")
                        
                        # 处理内容
                        if raw_content:
                            # 处理Unicode编码
                            if isinstance(raw_content, str):
                                content = raw_content
                
                # 如果未从标准字段找到内容，检查fallback字段
                if not content:
                    for field in ['content', 'text', 'message', 'result', 'data', 'response']:
                        if field in response and isinstance(response[field], str):
                            content = response[field]
                            logger.debug(f"从备选字段'{field}'获取内容")
                            break
            
            # 如果响应本身就是字符串
            elif isinstance(response, str):
                content = response
                logger.debug("响应本身是字符串，直接使用")
            
            # 如果仍未找到内容，尝试将整个响应转为字符串
            if not content and response:
                try:
                    content = json.dumps(response, ensure_ascii=False)
                    logger.debug("将整个响应转换为JSON字符串")
                except Exception as e:
                    logger.error(f"转换响应为字符串失败: {str(e)}")
            
            if not content:
                logger.error("API响应中未找到有效内容")
                return {"error": "无法从API响应中获取内容"}
            
            # 先看看是否能直接解析JSON
            try:
                # 尝试识别和提取JSON部分
                json_match = re.search(r'```json\s*([\s\S]*?)```', content)
                if json_match:
                    json_str = json_match.group(1).strip()
                    logger.debug(f"找到JSON代码块，长度:{len(json_str)}")
                    json_result = json.loads(json_str)
                    logger.debug("成功解析JSON代码块")
                    return json_result
            except Exception as json_err:
                logger.debug(f"解析JSON代码块失败: {str(json_err)}")
            
            # 看看是否有结构化的格式
            logger.debug("尝试从Markdown/文本中提取")
            
            # 提取评分数据
            json_result = {}
            
            # 尝试提取总分和等级
            score_pattern = r'(?:总[得评]分|得分|总分|score)[：:]\s*(\d+(?:\.\d+)?)'
            score_match = re.search(score_pattern, content, re.IGNORECASE)
            
            total_score = 0
            if score_match:
                try:
                    total_score = float(score_match.group(1))
                    logger.debug(f"成功提取总分: {total_score}")
                except ValueError:
                    logger.debug(f"提取到的总分无法转换为数字: {score_match.group(1)}")
            
            # 从中考评分报告中提取
            if "中考" in content and "得分" in content:
                try:
                    # 检查是否有综合得分的表示
                    synth_pattern = r'综合[得评]分[：:]\s*(\d+)/(\d+)'
                    synth_match = re.search(synth_pattern, content)
                    if synth_match:
                        score = float(synth_match.group(1))
                        max_score = float(synth_match.group(2))
                        total_score = score
                        logger.debug(f"从中考评分报告提取到综合得分: {score}/{max_score}")
                except Exception as e:
                    logger.debug(f"从中考评分提取总分失败: {str(e)}")
            
            # 提取等级信息
            level_pattern = r'(?:等级评定|等级|level)[：:]\s*([A-D](?:-)?(?:[+-])?)'
            level_match = re.search(level_pattern, content, re.IGNORECASE)
            
            level = "C"  # 默认等级
            if level_match:
                level = level_match.group(1)
                logger.debug(f"成功提取等级: {level}")
            
            # 从字符串中提取关键信息
            # 如果内容看起来像Deepseek中考评分报告
            if "广东中考" in content and "评分报告" in content:
                logger.debug("检测到广东中考评分报告格式")
                
                # 提取总分 (通常在"综合得分"或类似字段)
                synth_pattern = r'综合[得评]分[：:]\s*(\d+)[/／](\d+)'
                alt_pattern = r'[总综][得评]分[：:]\s*(\d+(?:\.\d+)?)'
                
                synth_match = re.search(synth_pattern, content)
                if synth_match:
                    total_score = float(synth_match.group(1))
                    logger.debug(f"从中考报告提取总分: {total_score}")
                else:
                    alt_match = re.search(alt_pattern, content)
                    if alt_match:
                        total_score = float(alt_match.group(1))
                        logger.debug(f"从替代模式提取总分: {total_score}")
                
                # 分项得分 (可能有"分项评分"部分)
                content_score = self._extract_subscore(content, ["内容充实度", "内容主旨", "内容分"], 12)
                language_score = self._extract_subscore(content, ["语言表达", "语言文采", "语言分"], 13)
                structure_score = self._extract_subscore(content, ["结构严谨性", "文章结构", "结构分"], 8)
                writing_score = self._extract_subscore(content, ["思想感情", "文面书写", "思想分"], 4)
                
                # 提取各分析段落
                overall_assessment = self._extract_paragraph(content, ["总评", "总体评价", "综合评价"])
                content_analysis = self._extract_paragraph(content, ["内容分析", "内容评价"])
                language_analysis = self._extract_paragraph(content, ["语言分析", "语言评价"])
                structure_analysis = self._extract_paragraph(content, ["结构分析", "结构评价"])
                improvement_suggestions = self._extract_paragraph(content, ["写作建议", "改进建议", "升格建议"])
                
                # 错别字仍采用原有正则方式提取
                spelling_errors = []
                error_pattern = r'(?:错别字|拼写错误)[：:]\s*\[(.*?)\]'
                error_match = re.search(error_pattern, content, re.DOTALL)
                if error_match:
                    errors_text = error_match.group(1)
                    errors = re.findall(r'["\']([^"\']*)["\']', errors_text)
                    spelling_errors = errors
                    logger.debug(f"成功提取错别字列表，数量: {len(errors)}")
                
                # 构建完整结果
                return {
                    "总得分": total_score,
                    "level": level,
                    "分项得分": {
                        "内容主旨": content_score,
                        "语言文采": language_score,
                        "文章结构": structure_score,
                        "文面书写": writing_score
                    },
                    "total_score": total_score,
                    "content_score": content_score,
                    "language_score": language_score,
                    "structure_score": structure_score,
                    "writing_score": writing_score,
                    "overall_assessment": overall_assessment,
                    "content_analysis": content_analysis,
                    "language_analysis": language_analysis,
                    "structure_analysis": structure_analysis,
                    "improvement_suggestions": improvement_suggestions,
                    "总体评价": overall_assessment,
                    "内容分析": content_analysis,
                    "语言分析": language_analysis,
                    "结构分析": structure_analysis,
                    "写作建议": improvement_suggestions,
                    "spelling_errors": {
                        "解析": spelling_errors
                    },
                    "错别字": spelling_errors
                }
            
        except Exception as e:
            logger.error(f"提取Deepseek响应数据时发生错误: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return self._create_empty_result(error=str(e))

    # 添加辅助方法用于提取中考评分报告中的分项得分
    def _extract_subscore(self, content: str, field_names: List[str], default_value: int = 0) -> int:
        """从内容中提取分项得分"""
        for field in field_names:
            pattern = rf'{field}[：:]\s*(\d+(?:\.\d+)?)/\d+'
            alt_pattern = rf'{field}[：:]\s*(\d+(?:\.\d+)?)'
            
            match = re.search(pattern, content)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
            
            # 尝试替代模式
            alt_match = re.search(alt_pattern, content)
            if alt_match:
                try:
                    return float(alt_match.group(1))
                except ValueError:
                    pass
                    
        return default_value
    
    # 添加辅助方法用于提取各类分析段落
    def _extract_paragraph(self, content: str, field_names: List[str]) -> str:
        """从内容中提取特定段落"""
        for field in field_names:
            pattern = rf'{field}[：:](.*?)(?=\n\n|\n[^\n]+[：:]|$)'
            
            match = re.search(pattern, content, re.DOTALL)
            if match:
                text = match.group(1).strip()
                if text:
                    # 去除可能的子标题和项目符号
                    text = re.sub(r'^\s*[-•*]|\n\s*[-•*]', '', text)
                    return text
        
        return ""
    
    def _create_empty_result(self, error=None):
        """
        创建一个空的结果结构
        """
        result = {
            "总得分": 0,
            "level": "D",
            "分项得分": {
                "内容主旨": 0,
                "语言文采": 0,
                "文章结构": 0,
                "文面书写": 0
            },
            "total_score": 0,
            "content_score": 0,
            "language_score": 0,
            "structure_score": 0,
            "writing_score": 0,
            "overall_assessment": "未能生成评价",
            "content_analysis": "未能生成分析",
            "language_analysis": "未能生成分析",
            "structure_analysis": "未能生成分析",
            "improvement_suggestions": "未能生成建议",
            "总体评价": "未能生成评价",
            "内容分析": "未能生成分析",
            "language_analysis": "未能生成分析",
            "structure_analysis": "未能生成分析",
            "写作建议": "未能生成建议",
            "spelling_errors": {
                "解析": []
            },
            "错别字": []
        }
        
        if error:
            result["error"] = error
            
        return result

    def _create_mock_result(self, content: str) -> Dict:
        """
        当JSON解析失败时，尝试从文本中提取信息生成模拟结果
        
        Args:
            content: 原始响应内容
            
        Returns:
            Dict: 模拟生成的结果
        """
        logger.warning("生成模拟结果以应对JSON解析失败")
        
        # 如果内容为空，返回默认结果
        if not content or content.strip() == "":
            return self._create_default_result("API返回空内容")
            
        result = self._create_empty_result()
        
        try:
            # 尝试提取分数
            score_match = re.search(r'总[分得]分[：:]\s*(\d+)', content)
            if score_match:
                result["总得分"] = int(score_match.group(1))
                result["total_score"] = int(score_match.group(1))
            else:
                # 如果没有找到分数，使用默认分数
                result["总得分"] = 40
                result["total_score"] = 40
            
            # 尝试提取分项得分
            content_score_match = re.search(r'内容主旨[：:]\s*(\d+)', content)
            if content_score_match:
                result["分项得分"]["内容主旨"] = int(content_score_match.group(1))
                result["content_score"] = int(content_score_match.group(1))
            else:
                result["分项得分"]["内容主旨"] = 16
                result["content_score"] = 16
            
            language_score_match = re.search(r'语言文采[：:]\s*(\d+)', content)
            if language_score_match:
                result["分项得分"]["语言文采"] = int(language_score_match.group(1))
                result["language_score"] = int(language_score_match.group(1))
            else:
                result["分项得分"]["语言文采"] = 12
                result["language_score"] = 12
            
            structure_score_match = re.search(r'文章结构[：:]\s*(\d+)', content)
            if structure_score_match:
                result["分项得分"]["文章结构"] = int(structure_score_match.group(1))
                result["structure_score"] = int(structure_score_match.group(1))
            else:
                result["分项得分"]["文章结构"] = 8
                result["structure_score"] = 8
            
            writing_score_match = re.search(r'文面书写[：:]\s*(\d+)', content)
            if writing_score_match:
                result["分项得分"]["文面书写"] = int(writing_score_match.group(1))
                result["writing_score"] = int(writing_score_match.group(1))
            else:
                result["分项得分"]["文面书写"] = 4
                result["writing_score"] = 4
            
            # 尝试提取评价
            assessment_match = re.search(r'总体评价[：:](.*?)(?:内容分析|分项得分|语言分析|结构分析|写作建议|$)', content, re.DOTALL)
            if assessment_match:
                assessment = assessment_match.group(1).strip()
                if assessment:
                    result["总体评价"] = assessment
                    result["overall_assessment"] = assessment
            else:
                result["总体评价"] = "由于API响应格式问题，无法提取详细评价。这是一个模拟评分。"
                result["overall_assessment"] = "由于API响应格式问题，无法提取详细评价。这是一个模拟评分。"
            
            # 尝试提取内容分析
            content_analysis_match = re.search(r'内容分析[：:](.*?)(?:总体评价|分项得分|语言分析|结构分析|写作建议|$)', content, re.DOTALL)
            if content_analysis_match:
                analysis = content_analysis_match.group(1).strip()
                if analysis:
                    result["内容分析"] = analysis
                    result["content_analysis"] = analysis
            else:
                result["内容分析"] = "由于API响应格式问题，无法提取详细分析。"
                result["content_analysis"] = "由于API响应格式问题，无法提取详细分析。"
            
            # 添加模拟标记
            result["is_mock"] = True
            result["mock_reason"] = "JSON解析失败，使用正则表达式提取信息"
            
            # 根据总分确定等级
            total_score = result["总得分"] 
            if total_score >= 43:
                result["level"] = "A"
            elif total_score >= 35:
                result["level"] = "B"
            elif total_score >= 27:
                result["level"] = "C"
            else:
                result["level"] = "D"
                
            return result
            
        except Exception as e:
            logger.error(f"生成模拟结果失败: {str(e)}")
            # 返回默认结果
            return self._create_default_result(f"生成模拟结果失败: {str(e)}")

    def _create_default_result(self, reason: str) -> Dict:
        """
        创建一个默认的结果结构，用于API调用失败时返回
        
        Args:
            reason: 失败原因
            
        Returns:
            Dict: 默认结果
        """
        logger.warning(f"生成默认结果: {reason}")
        
        # 创建一个基本的评分结果
        result = {
            "总得分": 40,  # 设置一个中等分数，而不是0分
            "level": "B",
            "分项得分": {
                "内容主旨": 16,
                "语言文采": 12,
                "文章结构": 8,
                "文面书写": 4
            },
            "total_score": 40,
            "content_score": 16,
            "language_score": 12, 
            "structure_score": 8,
            "writing_score": 4,
            "overall_assessment": "由于API调用问题，无法生成详细评价。这是一个默认评分。",
            "content_analysis": "由于API调用问题，无法生成详细分析。",
            "language_analysis": "由于API调用问题，无法生成详细分析。",
            "structure_analysis": "由于API调用问题，无法生成详细分析。",
            "improvement_suggestions": "由于API调用问题，无法生成详细建议。",
            "总体评价": "由于API调用问题，无法生成详细评价。这是一个默认评分。",
            "内容分析": "由于API调用问题，无法生成详细分析。",
            "language_analysis": "由于API调用问题，无法生成详细分析。",
            "structure_analysis": "由于API调用问题，无法生成详细分析。",
            "写作建议": "由于API调用问题，无法生成详细建议。",
            "spelling_errors": {
                "解析": []
            },
            "错别字": [],
            "is_default": True,  # 标记为默认结果
            "default_reason": reason  # 记录默认原因
        }
        
        return result

    @log_api_call_async
    async def _call_api_async(self, messages: List[Dict[str, str]], **kwargs) -> Dict:
        """
        异步调用API并处理响应
        
        Args:
            messages: 消息列表
            
        Returns:
            Dict: API响应
            
        Raises:
            APIError: API调用错误
        """
        try:
            print(f"[DeepseekClient] 开始异步API调用，消息数: {len(messages)}")
            logger.info(f"[DeepseekClient] 开始异步API调用，消息数: {len(messages)}")
            
            # 记录API请求配置
            api_config = {
                "url": self.api_base,
                "model": self.model,
                "temperature": self.api_config.get("temperature", 0.1),
                "timeout": self.api_config['timeout']
            }
            print(f"[DeepseekClient] API配置: {api_config}")
            logger.info(f"[DeepseekClient] API配置: {api_config}")
            
            # 创建完整的API请求参数
            request_params = {
                        "model": self.model,
                        "messages": messages,
                "temperature": self.api_config.get("temperature", 0.1),
                **kwargs
            }
            
            # API请求开始时间
            api_start_time = datetime.now()
            
            # 打印请求前的时间戳
            print(f"[DeepseekClient] 发送API请求时间: {api_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            
            # 使用同步方式调用API
            try:
                print(f"[DeepseekClient] 使用同步方式调用API")
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.api_config.get("temperature", 0.1)
                }
                
                # 直接使用OpenAI SDK调用API
                response = openai.ChatCompletion.create(**request_params)
                
                # API请求结束时间
                api_end_time = datetime.now()
                
                # 打印请求后的时间戳
                print(f"[DeepseekClient] 收到API响应时间: {api_end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                
                # 提取结果
                result = self._extract_result(response)
                
                success_result = {
                    "status": "success",
                    "result": result
                }
                
                # 计算响应时间
                response_time = time.time() - api_start_time
                
                # 记录API调用结束
                api_monitor.log_api_response(
                    request_id=None,  # 这里可以根据需要传入request_id
                    status="success" if response.get("status") != "error" else "error",
                    response_time=response_time,
                    response=response
                )
                
                # 返回响应
                if isinstance(response, dict) and "status" in response and response["status"] == "success":
                    return response
                else:
                    # 如果response不是我们期望的格式，尝试提取结果
                    result = self._extract_result(response)
                    return {
                        "status": "success",
                        "result": result
                    }
            
            except Exception as e:
                print(f"[DeepseekClient] API调用过程中发生错误: {str(e)}")
                logger.error(f"[DeepseekClient] API调用过程中发生错误: {str(e)}")
                logger.error(f"[DeepseekClient] 错误详情: {traceback.format_exc()}")
                
                # 计算响应时间
                response_time = time.time() - api_start_time
                
                error_result = {
                    "status": "error",
                    "message": f"API调用失败: {str(e)}"
                }
                
                # 记录API调用结束（失败）
                api_monitor.log_api_response(
                    request_id=None,  # 这里可以根据需要传入request_id
                    status="error",
                    response_time=response_time,
                    error=str(e)
                )
                
                return error_result
            
        except Exception as e:
            print(f"[DeepseekClient] API调用异常: {str(e)}")
            logger.error(f"[DeepseekClient] API调用异常: {str(e)}")
            logger.error(f"[DeepseekClient] 异常详情: {traceback.format_exc()}")
            # 返回默认评分和错误信息
            return {
                "status": "error",
                "message": f"API调用异常: {str(e)}",
                "result": self._create_default_result(f"API调用异常: {str(e)}")
            }

    
    @log_api_call
    def correct_essay(self, content: str) -> Dict[str, Any]:
        """批改作文并返回标准化结果
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 批改结果，标准格式为：
            {
                "status": "success" | "error",
                "result": {
                    "总得分": 分数,
                    "分项得分": {
                        "内容主旨": 分数,
                        "语言文采": 分数,
                        "文章结构": 分数,
                        "文面书写": 分数
                    },
                    "总体评价": 评价文字,
                    "内容分析": 内容分析,
                    "语言分析": 语言分析,
                    "结构分析": 结构分析,
                    "写作建议": 改进建议,
                    "错别字": [错误列表]
                } | {"message": 错误信息}
            }
        """
        try:
            print(f"[DeepseekClient] 开始批改作文，内容长度: {len(content)}")
            logger.info(f"[DeepseekClient] 开始批改作文，内容长度: {len(content)}")
            
            # 记录API调用开始
            api_call_id = api_monitor.log_api_call(
                provider=self.provider_name,
                model=self.model,
                endpoint="correct_essay",
                request_params={"content_length": len(content)},
                function="correct_essay"
            )
            
            # 记录开始时间
            start_time = time.time()
            
            # 计算预估token数（中文每个字约2-3个token）
            estimated_tokens = len(content) * 3
            
            # 如果预估token数超过限制，分块处理
            if estimated_tokens > self.api_config['chunk_size']:
                print(f"[DeepseekClient] 内容较长，将分块处理，预估token数: {estimated_tokens}")
                logger.info(f"[DeepseekClient] 内容较长，将分块处理，预估token数: {estimated_tokens}")
                result = self._process_long_content(content)
                
                # 计算响应时间
                response_time = time.time() - start_time
                
                # 记录API调用结束
                api_monitor.log_api_response(
                    request_id=api_call_id,
                    status="success" if result.get("status") != "error" else "error",
                    response_time=response_time,
                    response=result
                )
                
                return result
            
            system_prompt = f"""你是一位专业的语文教师，现在需要你按照广东中考语文作文评分标准对一篇作文进行全面评分和详细分析。

【作文评分标准】
总分50分
字数要求600字以上

【评分等级划分】
A级（43-50分）：内容立意明确，中心突出，材料具体生动，有真情实感；语言得体、流畅；结构严谨，注意照应，详略得当；卷面整洁，书写优美。
B级（35-42分）：内容立意明确，中心突出，材料具体；语言规范、通顺；结构完整，条理清楚；卷面整洁，书写工整。
C级（27-34分）：内容立意明确，材料能表现中心；语言基本通顺，有少数错别字；结构基本完整，有条理；卷面较为整洁，书写清楚。
D级（0-26分）：内容立意不明确，材料难以表现中心；语言不通顺，错别字较多；结构不完整，条理不清楚；卷面脏乱，字迹潦草。

【评分维度权重】
各项分数必须为整数，且必须严格按照以下权重范围分配：
1. 内容主旨：占总分的30%-40%（最高20分，最低视作文质量定）
2. 语言文采：占总分的20%-30%（最高15分，最低视作文质量定）
3. 文章结构：占总分的10%-20%（最高10分，最低视作文质量定）
4. 文面书写：占总分的0%-10%（最高5分，最低视作文质量定）

【具体扣分项】
1. 无标题扣2分
2. 字数不足：低于600字，每少50字扣1分
3. 错别字：每个错别字扣1分
4. 标点符号使用不规范：根据严重程度1-3分

错别字扣分是从四项得分总和中直接扣除的，而非从某个分项中扣除。

字数：{len(content)}字

请提供以下信息，并确保只返回JSON格式的结果：
```
{{
    "总得分": 45,
    "分项得分": {{
        "内容主旨": 18,
        "语言文采": 14,
        "文章结构": 9,
        "文面书写": 4
    }},
    "总体评价": "这是一篇内容充实的文章，请在这里提供200字左右的总体评价。",
    "内容分析": "文章主题明确，论述有力，请在这里提供200字左右的内容分析。",
    "语言分析": "语言表达流畅，用词准确，请在这里提供200字左右的语言分析。",
    "结构分析": "文章结构合理，层次分明，请在这里提供200字左右的结构分析。",
    "写作建议": "建议在论述方面更加深入，请在这里提供200字左右的写作建议。",
    "错别字": ["错误1->正确1", "错误2->正确2"]
}}
```

请确保只返回JSON格式的结果，不要包含其他说明文字。每个分析字段控制在200字左右，避免过长。
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            
            print(f"[DeepseekClient] 准备调用API，发送作文内容进行批改")
            logger.info(f"[DeepseekClient] 准备调用API，发送作文内容进行批改")
            
            # 使用同步方式调用API
            try:
                print(f"[DeepseekClient] 使用同步方式调用API")
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.api_config.get("temperature", 0.1)
                }
                
                # 直接使用OpenAI SDK调用API
                response = openai.ChatCompletion.create(**request_params)
                
                # API请求结束时间
                api_end_time = datetime.now()
                
                # 打印请求后的时间戳
                print(f"[DeepseekClient] 收到API响应时间: {api_end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                
                # 提取结果
                result = self._extract_result(response)
                
                success_result = {
                    "status": "success",
                    "result": result
                }
                
                # 计算响应时间
                response_time = time.time() - start_time
                
                # 记录API调用结束
                api_monitor.log_api_response(
                    request_id=api_call_id,
                    status="success",
                    response_time=response_time,
                    response=success_result
                )
                
                return success_result
                
            except Exception as e:
                print(f"[DeepseekClient] API调用过程中发生错误: {str(e)}")
                logger.error(f"[DeepseekClient] API调用过程中发生错误: {str(e)}")
                logger.error(f"[DeepseekClient] 错误详情: {traceback.format_exc()}")
                
                # 计算响应时间
                response_time = time.time() - start_time
                
                error_result = {
                    "status": "error",
                    "message": f"API调用失败: {str(e)}"
                }
                
                # 记录API调用结束（失败）
                api_monitor.log_api_response(
                    request_id=api_call_id,
                    status="error",
                    response_time=response_time,
                    error=str(e)
                )
                
                return error_result
                
        except Exception as e:
            print(f"[DeepseekClient] 批改作文失败: {str(e)}")
            logger.error(f"[DeepseekClient] 批改作文失败: {str(e)}")
            logger.error(f"[DeepseekClient] 错误详情: {traceback.format_exc()}")
            
            return {
                "status": "error",
                "message": f"批改作文失败: {str(e)}"
            }

    def _process_long_content(self, content: str) -> Dict[str, Any]:
        """
        处理长文本内容，将其分块处理
        """
        try:
            # 按句子分割内容
            sentences = re.split(r'([。！？])', content)
            chunks = []
            current_chunk = ""
            
            # 组合句子成块
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                else:
                    sentence = sentences[i]
                
                if len(current_chunk) + len(sentence) <= self.api_config['chunk_size']:
                    current_chunk += sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # 处理每个块
            results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"处理第{i + 1}/{len(chunks)}块，长度: {len(chunk)}")
                result = self.correct_essay(chunk)
                if result['status'] == 'success':
                    results.append(result['result'])
                else:
                    raise Exception(f"处理第{i + 1}块时失败: {result['message']}")
            
            # 合并结果
            return {
                "status": "success",
                "result": self._merge_results(results)
            }
            
        except Exception as e:
            logger.error(f"处理长文本失败: {str(e)}")
            return {
                "status": "error",
                "message": f"处理长文本失败: {str(e)}"
            }
    
    def _merge_results(self, results: List[Dict]) -> Dict:
        """
        合并多个批改结果
        """
        if not results:
            return {}
            
        # 计算平均分数
        total_score = sum(r.get('total_score', 0) for r in results) / len(results)
        content_score = sum(r.get('content_score', 0) for r in results) / len(results)
        language_score = sum(r.get('language_score', 0) for r in results) / len(results)
        structure_score = sum(r.get('structure_score', 0) for r in results) / len(results)
        writing_score = sum(r.get('writing_score', 0) for r in results) / len(results)
        
        # 合并文本分析
        overall_assessment = "\n".join(r.get('overall_assessment', '') for r in results)
        content_analysis = "\n".join(r.get('content_analysis', '') for r in results)
        language_analysis = "\n".join(r.get('language_analysis', '') for r in results)
        structure_analysis = "\n".join(r.get('structure_analysis', '') for r in results)
        improvement_suggestions = "\n".join(r.get('improvement_suggestions', '') for r in results)
        
        # 合并错别字
        spelling_errors = []
        for r in results:
            if 'spelling_errors' in r and isinstance(r['spelling_errors'], dict):
                spelling_errors.extend(r['spelling_errors'].get('解析', []))
        
        return {
            "total_score": round(total_score, 1),
            "content_score": round(content_score, 1),
            "language_score": round(language_score, 1),
            "structure_score": round(structure_score, 1),
            "writing_score": round(writing_score, 1),
            "overall_assessment": overall_assessment,
            "content_analysis": content_analysis,
            "language_analysis": language_analysis,
            "structure_analysis": structure_analysis,
            "improvement_suggestions": improvement_suggestions,
            "spelling_errors": {
                "解析": spelling_errors
            }
        }

    def analyze_essay(self, content: str) -> Dict[str, Any]:
        """
        分析作文（与 correct_essay 方法相同，保持向后兼容）
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 分析结果
        """
        return self.correct_essay(content)

    @log_api_call_async
    async def correct_essay_async(self, content: str) -> Dict[str, Any]:
        """
        异步批改作文
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 批改结果
        """
        try:
            print(f"[DeepseekClient] 异步批改作文，内容长度: {len(content)}")
            logger.info(f"[DeepseekClient] 异步批改作文，内容长度: {len(content)}")
            
            # 记录API调用开始
            api_monitor.log_api_call(
                provider=self.provider_name,
                model=self.model,
                endpoint="correct_essay_async",
                request_params={"content_length": len(content)},
                function="correct_essay_async",
                is_async=True
            )
            
            # 计算预估token数
            estimated_tokens = len(content) * 3
            
            # 如果预估token数超过限制，分块处理
            if estimated_tokens > self.api_config['chunk_size']:
                print(f"[DeepseekClient] 内容较长，将分块处理，预估token数: {estimated_tokens}")
                logger.info(f"[DeepseekClient] 内容较长，将分块处理，预估token数: {estimated_tokens}")
                return await self._process_long_content_async(content)
            
            system_prompt = f"""你是一位专业的语文教师，现在需要你按照广东中考语文作文评分标准对一篇作文进行全面评分和详细分析。
            
            // ... 省略相同的prompt内容 ...
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            
            # 记录开始时间
            start_time = time.time()
            
            # 直接调用异步API
            response = await self._call_api_async(messages)
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 记录API调用结束
            api_monitor.log_api_response(
                request_id=None,  # 这里可以根据需要传入request_id
                status="success" if response.get("status") != "error" else "error",
                response_time=response_time,
                response=response
            )
            
            # 返回响应
            if isinstance(response, dict) and "status" in response and response["status"] == "success":
                return response
            else:
                # 如果response不是我们期望的格式，尝试提取结果
                result = self._extract_result(response)
                return {
                    "status": "success",
                    "result": result
                }
            
        except Exception as e:
            print(f"[DeepseekClient] 异步批改作文失败: {str(e)}")
            logger.error(f"[DeepseekClient] 异步批改作文失败: {str(e)}")
            logger.error(f"[DeepseekClient] 错误详情: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"异步批改作文失败: {str(e)}"
            }

    async def _process_long_content_async(self, content: str) -> Dict[str, Any]:
        """
        异步处理长文本内容，将其分块处理
        
        Args:
            content: 长文本内容
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 按句子分割内容
            sentences = re.split(r'([。！？])', content)
            chunks = []
            current_chunk = ""
            
            # 组合句子成块
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                else:
                    sentence = sentences[i]
                
                if len(current_chunk) + len(sentence) <= self.api_config['chunk_size']:
                    current_chunk += sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # 处理每个块
            results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"处理第{i + 1}/{len(chunks)}块，长度: {len(chunk)}")
                result = await self.correct_essay_async(chunk)
                if result['status'] == 'success':
                    results.append(result['result'])
                else:
                    raise Exception(f"处理第{i + 1}块时失败: {result['message']}")
            
            # 合并结果
            return {
                "status": "success",
                "result": self._merge_results(results)
            }
            
        except Exception as e:
            logger.error(f"异步处理长文本失败: {str(e)}")
            return {
                "status": "error",
                "message": f"异步处理长文本失败: {str(e)}"
            } 