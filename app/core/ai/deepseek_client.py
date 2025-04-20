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
from typing import Dict, Any, List, Optional, Union, Tuple
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
import importlib.metadata
import pkg_resources

from app.core.ai.api_client import BaseAPIClient, APIError
from app.core.ai.api_monitor import log_api_call, log_api_call_async, api_monitor
from config.ai_config import AI_CONFIG

# 检查OpenAI版本
try:
    # 尝试多种方法获取openai版本
    try:
        openai_version = importlib.metadata.version("openai")
    except:
        try:
            openai_version = pkg_resources.get_distribution("openai").version
        except:
            openai_version = "unknown"
    
    # 导入OpenAI SDK
    import openai
    
    # 判断是否为新版OpenAI SDK (>= 1.0.0)
    is_new_openai_sdk = openai_version.split('.')[0] != '0'
    
    if is_new_openai_sdk:
        from openai import OpenAI
        logging.info(f"使用OpenAI新版SDK: {openai_version}")
    else:
        logging.info(f"使用OpenAI旧版SDK: {openai_version}")
        
except ImportError:
    logging.error("未安装OpenAI SDK，请执行 pip install openai")
    is_new_openai_sdk = False

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
        
        # 添加最大内容长度属性
        self.max_content_length = 8000  # 最大处理字符数
        
        # 根据OpenAI SDK版本设置客户端
        global is_new_openai_sdk
        try:
            if is_new_openai_sdk:
                self.openai_client = OpenAI(api_key=self.api_key, base_url=self.api_base)
                logger.info("已初始化新版OpenAI客户端")
            else:
                # 设置OpenAI全局配置
                openai.api_key = self.api_key
                openai.api_base = self.api_base
                logger.info("已设置旧版OpenAI全局配置")
        except Exception as e:
            logger.error(f"初始化OpenAI客户端失败: {str(e)}")
            
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
            
            # 如果未找到有效内容，返回默认评分
            if not content or content.strip() == "":
                logger.warning("API响应中未找到有效内容，返回默认评分")
                return self._create_default_result("API响应内容为空")
            
            # 先看看是否能直接解析JSON
            try:
                # 尝试直接解析整个内容为JSON
                try:
                    json_result = json.loads(content)
                    logger.debug("成功直接解析内容为JSON")
                    
                    # 验证JSON结果是否包含必要字段
                    if "总得分" in json_result and "分项得分" in json_result:
                        logger.info("解析到有效的评分结果")
                        return json_result
                except json.JSONDecodeError:
                    # 如果整个内容不是有效JSON，尝试提取代码块
                    pass
                    
                # 尝试识别和提取JSON代码块
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
                if json_match:
                    json_str = json_match.group(1).strip()
                    logger.debug(f"找到JSON代码块，长度:{len(json_str)}")
                    json_result = json.loads(json_str)
                    logger.debug("成功解析JSON代码块")
                    return json_result
            except Exception as json_err:
                logger.debug(f"解析JSON块失败: {str(json_err)}")
            
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
            
            # 如果没有找到任何有效得分，返回默认评分
            if total_score == 0:
                logger.warning("未能从响应中提取到有效得分，返回默认评分")
                return self._create_default_result("未能提取有效评分")
            
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
                    "language_analysis": language_analysis,
                    "structure_analysis": structure_analysis,
                    "写作建议": improvement_suggestions,
                    "spelling_errors": {
                        "解析": spelling_errors
                    },
                    "错别字": spelling_errors
                }

            # 如果不是中考格式，尝试创建基本结果
            # 从文本中尽可能提取评分信息
            logger.info(f"尝试从普通文本中提取评分信息，获取到总分: {total_score}")
            
            # 估算分项得分
            content_score = self._extract_subscore(content, ["内容", "主旨", "内容分"], int(total_score * 0.4))
            language_score = self._extract_subscore(content, ["语言", "文采", "语言分"], int(total_score * 0.3))
            structure_score = self._extract_subscore(content, ["结构", "布局", "结构分"], int(total_score * 0.2))
            writing_score = self._extract_subscore(content, ["文面", "书写", "错别字"], int(total_score * 0.1))
            
            # 提取文本评价
            overall_assessment = self._extract_paragraph(content, ["总评", "总体评价", "评价"])
            content_analysis = self._extract_paragraph(content, ["内容分析", "内容"])
            language_analysis = self._extract_paragraph(content, ["语言分析", "语言"])
            structure_analysis = self._extract_paragraph(content, ["结构分析", "结构"])
            improvement_suggestions = self._extract_paragraph(content, ["建议", "改进"])
            
            # 如果没有提取到评价，使用完整内容作为总体评价
            if not overall_assessment:
                overall_assessment = content[:300] if len(content) > 300 else content
            
            # 返回构建的结果
            return {
                "总得分": total_score,
                "level": level,
                "分项得分": {
                    "内容主旨": content_score,
                    "语言文采": language_score,
                    "文章结构": structure_score,
                    "文面书写": writing_score
                },
                "总体评价": overall_assessment or "系统从AI响应中提取评价信息",
                "内容分析": content_analysis or "系统无法从AI响应中提取内容分析",
                "语言分析": language_analysis or "系统无法从AI响应中提取语言分析",
                "结构分析": structure_analysis or "系统无法从AI响应中提取结构分析",
                "写作建议": improvement_suggestions or "系统无法从AI响应中提取写作建议",
                "错别字": [],
                "api_extraction_method": "text_parsing"  # 标记使用了文本解析方法
                }
            
        except Exception as e:
            logger.error(f"提取Deepseek响应数据时发生错误: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return self._create_default_result(error=str(e))

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
    
    def _create_empty_result(self, error_message, essay_content=None):
        """创建空批改结果，包含错误信息"""
        logger.warning(f"创建空批改结果: {error_message}")
        
        # 估算文章长度作为基础评分依据
        base_score = 30
        content_length = len(essay_content) if essay_content else 0
        length_factor = min(10, max(0, content_length - 300) // 100)
        score = base_score + length_factor
        
        return {
            "错误": error_message,
            "总得分": score,
            "分项得分": {
                "内容主旨": int(score * 0.35),
                "语言文采": int(score * 0.25),
                "文章结构": int(score * 0.2),
                "文面书写": int(score * 0.2)
            },
            "总体评价": f"由于技术原因无法完成批改，系统已生成临时评分。错误: {error_message}",
            "内容分析": "无法分析内容，API调用失败。",
            "语言分析": "无法分析语言，API调用失败。",
            "结构分析": "无法分析结构，API调用失败。",
            "写作建议": "建议重新提交作文以获取完整评价。",
            "错别字": [],
            "is_error_result": True,
            "error_details": {
                "message": error_message,
                "timestamp": datetime.now().isoformat()  # 修正datetime调用
            }
        }

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

    def _create_default_result(self, error_message: str) -> Dict:
        """
        创建默认的批改结果（当API调用失败时使用）
        
        Args:
            error_message: 错误信息
            
        Returns:
            Dict: 默认的批改结果
        """
        return {
            "总得分": 50,
            "分项得分": {
                "内容主旨": 20,
                "语言文采": 15,
                "文章结构": 10,
                "文面书写": 5
            },
            "总体评价": f"由于技术原因无法完成完整批改。错误信息：{error_message}",
            "内容分析": "无法评估",
            "语言分析": "无法评估", 
            "结构分析": "无法评估",
            "写作建议": "请稍后重试",
            "错别字": [],
            "修改建议": "请稍后再次提交批改"
        }
        
    def correct_essay(self, essay_content: str, title: str = None, essay_type: str = None, prompt: str = None) -> Dict:
        """
        批改作文并返回详细评分和建议
        
        Args:
            essay_content: 作文内容
            title: 作文标题，可选
            essay_type: 作文类型，可选，如"记叙文"、"议论文"等
            prompt: 写作提示，可选
            
        Returns:
            Dict: 包含评分和建议的字典
        """
        # 检查内容长度并截断过长内容
        max_content_length = 7000  # 大约4000-5000个汉字
        
        essay_content, warning = self._handle_long_content(essay_content, max_content_length)
        
        if warning:
            logger.warning(warning)
            
        # 记录处理信息
        logger.info(f"开始批改作文，内容长度：{len(essay_content)}字符，标题：{title or '无'}")
        
        # 准备消息
        messages = self._prepare_correction_messages(essay_content, title, essay_type, prompt)
        
        # 调用API，包含重试机制
        max_retries = 3
        retry_delay = 2  # 初始延迟2秒
        
        for attempt in range(max_retries):
            try:
                logger.info(f"正在发送API请求（尝试 {attempt+1}/{max_retries}）")
                
                # 使用字典传递参数，避免显式设置response_format
                api_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,  # 使用较低的温度以获得更一致的结果
                    "max_tokens": 4000,  # 为详细的批改结果提供足够的token
                    "timeout": 60  # 设置60秒超时
                }
                
                response = self.openai_client.chat.completions.create(**api_params)
                
                # 提取结果
                correction_result = self._extract_result(response.model_dump())
                
                # 校验结果格式
                if self._validate_correction_result_format(correction_result):
                    # 确保在结果中添加状态字段，无论总分是否为0，只要格式有效就视为成功
                    return {
                    "status": "success",
                        "result": correction_result
                    }
                else:
                    error_msg = "API返回的结果格式无效"
                    logger.error(error_msg)
                    return {
                        "status": "error",
                        "message": error_msg,
                        "result": self._create_default_result(error_msg)
                    }
                    
            except openai.RateLimitError as e:
                logger.warning(f"触发速率限制（尝试 {attempt+1}/{max_retries}）：{str(e)}")
                if attempt < max_retries - 1:
                    sleep_time = retry_delay * (2 ** attempt)  # 指数退避策略
                    logger.info(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"达到最大重试次数，无法完成批改：{str(e)}")
                    return {
                        "status": "error",
                        "message": f"速率限制：{str(e)}",
                        "result": self._create_default_result(f"速率限制：{str(e)}")
                    }
                    
            except openai.APITimeoutError as e:
                logger.warning(f"API超时（尝试 {attempt+1}/{max_retries}）：{str(e)}")
                if attempt < max_retries - 1:
                    sleep_time = retry_delay  # 固定延迟重试
                    logger.info(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"达到最大重试次数，API持续超时：{str(e)}")
                    return {
                        "status": "error",
                        "message": f"API超时：{str(e)}",
                        "result": self._create_default_result(f"API超时：{str(e)}")
                    }
            
            except Exception as e:
                logger.error(f"批改作文时发生错误：{str(e)}")
                logger.error(traceback.format_exc())
                return {
                    "status": "error",
                    "message": f"未知错误：{str(e)}",
                    "result": self._create_default_result(f"未知错误：{str(e)}")
                }
                
        # 如果执行到这里，说明所有重试都失败了
        logger.error("所有API调用尝试均失败")
        return {
            "status": "error",
            "message": "达到最大重试次数后仍无法获取有效结果",
            "result": self._create_default_result("达到最大重试次数后仍无法获取有效结果")
        }

    def _handle_long_content(self, content: str, max_length: int) -> Tuple[str, Optional[str]]:
        """
        处理过长的文本内容

        Args:
            content: 原始内容
            max_length: 最大允许长度

        Returns:
            Tuple[str, Optional[str]]: 处理后的内容和警告信息（如果有）
        """
        if len(content) <= max_length:
            return content, None
            
        warning = f"内容超过最大长度限制({len(content)}>{max_length}字)，已截取前{max_length}字进行处理"
        logger.warning(warning)
        
        # 简单截取方式，可以根据需要改进为更智能的分段处理
        truncated_content = content[:max_length]
        
        return truncated_content, warning
    
    def _prepare_correction_messages(self, content: str, title: str = None, essay_type: str = None, prompt: str = None) -> List[Dict]:
        """
        准备用于批改作文的消息列表
        
        Args:
            content: 作文内容
            title: 作文标题
            essay_type: 作文类型
            prompt: 写作提示
            
        Returns:
            List[Dict]: 准备好的消息列表
        """
        # 构造系统提示词
        system_prompt = """你是专业的中文作文批改老师，擅长分析文章结构、内容、语言和表达，能够提供详尽的评价和建议。
请对以下作文进行详细批改，评分标准满分为50分。在评分时要特别注意以下几点：
1. 内容是否符合主题、深刻、有创意
2. 语言是否流畅、准确、有文采
3. 结构是否清晰、层次分明
4. 是否存在错别字、语法错误、标点符号使用错误
5. 论据是否充分、论证是否有力（议论文）
6. 情感表达是否真挚、细腻（记叙文、散文）
7. 想象是否丰富、创新（想象文）

请按以下格式返回评价结果：

总得分：总体得分（50分制）

分项得分：
- 内容主旨：内容方面的得分（25分制）
- 语言文采：语言表达方面的得分（25分制）
- 文章结构：结构方面的得分（25分制）
- 文面书写：错别字、语法等方面的得分（25分制）

总体评价：整体评价和主要优缺点

内容分析：对内容的具体点评

语言分析：对语言表达的具体点评

结构分析：对结构的具体点评

写作建议：文章需要改进的地方（列出2-4点）

错别字：列出文章中的错别字、语法错误、标点符号使用错误等

修改建议：对文章进行具体的修改建议

请确保评分公正客观，点评详细具体，并给出切实可行的改进建议。"""

        # 如果有作文类型，添加相应的指导
        if essay_type:
            essay_type_guides = {
                "记叙文": "记叙文批改要注重情节发展、人物刻画、环境描写和情感表达的真实性和感染力。",
                "议论文": "议论文批改要注重论点是否明确，论据是否充分，论证是否有力，语言是否严谨。",
                "说明文": "说明文批改要注重说明对象是否明确，说明方法是否得当，语言是否准确简明。",
                "应用文": "应用文批改要注重格式是否规范，内容是否符合应用场景，语言是否得体。",
                "散文": "散文批改要注重抒情性、形象性、语言的优美性以及思想内涵的深度。"
            }
            
            if essay_type in essay_type_guides:
                system_prompt += f"\n\n{essay_type_guides[essay_type]}"
            else:
                logger.warning(f"未识别的作文类型: {essay_type}")
        
        # 构造用户消息
        user_message = ""
        if title:
            user_message += f"标题：{title}\n\n"
        
        if prompt:
            user_message += f"写作提示：{prompt}\n\n"
        
        user_message += f"作文内容：\n{content}"
        
        # 构造消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        logger.debug(f"已准备批改消息，系统提示词长度: {len(system_prompt)}字，用户消息长度: {len(user_message)}字")
        
        return messages
        
    def _validate_correction_result_format(self, result: Dict) -> bool:
        """
        验证批改结果的格式是否有效
        
        Args:
            result: 批改结果
            
        Returns:
            bool: 格式是否有效
        """
        # 检查必要字段是否存在
        required_fields = ["总得分", "总体评价"]
        
        for field in required_fields:
            if field not in result:
                logger.warning(f"批改结果缺少必要字段: {field}")
                return False
                
        # 检查总分是否为数字且在合理范围内
        try:
            score = float(result["总得分"])
            if not (0 <= score <= 50):
                logger.warning(f"总得分超出合理范围: {score}")
                return False
        except (ValueError, TypeError):
            logger.warning(f"总得分不是有效数字: {result['总得分']}")
            return False
            
        return True
        
    async def _handle_long_content_async(self, essay_content, title=None, essay_type=None, prompt=None):
        """异步处理过长内容的批改请求"""
        # 简单实现：截取有效长度进行处理
        max_safe_length = self.max_content_length - 500  # 留出安全余量
        truncated_content = essay_content[:max_safe_length]
        
        logger.warning(f"异步批改 - 内容已截断，从{len(essay_content)}字截至{len(truncated_content)}字")
        
        # 在结果中添加截断警告
        result = await self.correct_essay_async(truncated_content, title, essay_type, prompt)
        
        # 检查结果是否包含错误
        if result.get("status") == "success" and "result" in result:
            # 给结果添加截断警告
            result["result"]["内容截断警告"] = f"原文超过最大处理长度({len(essay_content)}字)，只分析了前{len(truncated_content)}字。"
            
            # 在总体评价中添加警告
            if "总体评价" in result["result"]:
                result["result"]["总体评价"] = f"[内容截断警告] {result['result']['总体评价']}"
        
        return result

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
    async def correct_essay_async(self, essay_content: str, title: str = None, essay_type: str = None, prompt: str = None) -> Dict[str, Any]:
        """
        异步批改作文
        
        Args:
            essay_content: 作文内容
            title: 作文标题，可选
            essay_type: 作文类型，可选
            prompt: 自定义提示词，可选
            
        Returns:
            Dict: 批改结果
        """
        try:
            # 对过长内容进行拆分处理
            if len(essay_content) > self.max_content_length:
                logger.warning(f"异步批改 - 作文内容过长({len(essay_content)}字)，将进行拆分处理")
                return await self._process_long_content_async(essay_content, title, essay_type, prompt)

            # 检查内容有效性
            self.validate_content(essay_content)
            
            # 准备发送到API的提示词
            messages = self._prepare_correction_messages(essay_content, title, essay_type, prompt)
            
            # 记录API请求信息
            logger.info(f"准备异步调用DeepSeek API进行批改，内容长度:{len(essay_content)}字，标题:{title}")
            
            # 实现重试机制
            max_retries = 3
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    # 增加重试间隔，根据重试次数递增
                    if retry_count > 0:
                        wait_time = 2 ** retry_count  # 指数退避: 2, 4, 8秒
                        logger.warning(f"异步批改 - 第{retry_count}次重试，等待{wait_time}秒后重试...")
                        await asyncio.sleep(wait_time)
                    
                    # 异步调用API
                    start_time = time.time()
                    response = await self._call_api_async(
                        messages=messages,
                        temperature=0.3,  # 使用较低的温度以获得更一致的结果
                        max_tokens=4000  # 为详细的批改结果提供足够的token
                    )
                    elapsed_time = time.time() - start_time
                    
                    # 提取并处理结果
                    result = self._extract_result(response)
                    
                    # 确保返回标准格式
                    try:
                        if hasattr(self, '_convert_to_standard_format'):
                            result = self._convert_to_standard_format(result)
                    except Exception as e:
                        logger.warning(f"转换结果到标准格式失败，使用原始结果: {str(e)}")
                    
                    # 添加API响应元数据
                    result["_meta"] = {
                        "api_response_time": elapsed_time,
                        "model": self.model,
                        "timestamp": datetime.now().isoformat(),
                        "async": True
                    }
                    
                    # 校验结果格式
                    if self._validate_correction_result_format(result):
                        return {
                            "status": "success",
                            "result": result
                        }
                    else:
                        logger.error("异步API返回的结果格式无效")
                        last_error = "无效的API响应格式"
                        retry_count += 1
                        continue
                    
                except openai.RateLimitError as e:
                    # 速率限制错误，等待更长时间再重试
                    logger.error(f"异步批改 - API速率限制错误: {str(e)}")
                    last_error = f"API速率限制: {str(e)}"
                    retry_count += 1
                    # 速率限制错误等待更长时间
                    await asyncio.sleep(5 + retry_count * 5)
                    continue
                    
                except openai.APITimeoutError as e:
                    # 超时错误
                    logger.error(f"异步批改 - API请求超时: {str(e)}")
                    last_error = f"API超时: {str(e)}"
                    retry_count += 1
                    continue
                    
                except openai.APIConnectionError as e:
                    # 连接错误
                    logger.error(f"异步批改 - API连接错误: {str(e)}")
                    last_error = f"API连接错误: {str(e)}"
                    retry_count += 1
                    continue
                    
                except openai.APIError as e:
                    # 一般API错误
                    logger.error(f"异步批改 - API错误: {str(e)}")
                    last_error = f"API错误: {str(e)}"
                    retry_count += 1
                    continue
                    
                except Exception as e:
                    # 其他未预期的错误
                    logger.error(f"异步批改 - 调用DeepSeek API时发生未预期错误: {str(e)}")
                    logger.exception(e)
                    last_error = f"未预期错误: {str(e)}"
                    retry_count += 1
                    continue
            
            # 所有重试都失败了，返回错误结果
            logger.error(f"异步批改 - 在{max_retries}次尝试后批改失败，最后错误: {last_error}")
            error_result = self._create_empty_result(
                error_message=f"异步API调用失败({max_retries}次尝试): {last_error}",
                essay_content=essay_content
            )
            return {
                "status": "error",
                "message": f"异步API调用失败({max_retries}次尝试): {last_error}",
                "result": error_result
            }
            
        except Exception as e:
            # 捕获所有其他错误
            logger.error(f"异步批改 - 作文批改过程中发生错误: {str(e)}")
            logger.exception(e)
            error_result = self._create_empty_result(
                error_message=f"异步批改处理错误: {str(e)}",
                essay_content=essay_content
            )
            return {
                "status": "error",
                "message": f"异步批改处理错误: {str(e)}",
                "result": error_result
            }

    async def _process_long_content_async(self, content: str, title: str = None, essay_type: str = None, prompt: str = None) -> Dict[str, Any]:
        """
        异步处理长文本内容，将其分块处理
        
        Args:
            content: 长文本内容
            title: 作文标题，可选
            essay_type: 作文类型，可选
            prompt: 自定义提示词，可选
            
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
                result = await self.correct_essay_async(chunk, title, essay_type, prompt)
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

    async def _call_api_async(self, messages, temperature=0.7, max_tokens=4000, **kwargs):
        """
        异步调用DeepSeek API
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            Dict: API响应
        """
        # 构建请求URL
        url = f"{self.api_base}/chat/completions"
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建请求参数
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 添加其他参数
        for key, value in kwargs.items():
            if key != 'response_format':  # 确保不添加response_format参数，因为deepseek-reasoner不支持
                data[key] = value
        
        logger.info(f"异步调用DeepSeek API: {url}")
        logger.debug(f"请求参数: {json.dumps(data)[:500]}...")
        
        # 使用httpx进行异步请求
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=60) as client:
            try:
                response = await client.post(
                    url,
                    json=data,
                    headers=headers
                )
                
                # 检查响应状态码
                response.raise_for_status()
                
                # 解析JSON响应
                result = response.json()
                logger.debug("API调用成功")
                return result
                
            except httpx.HTTPStatusError as e:
                # HTTP错误
                error_msg = f"HTTP错误: {e.response.status_code}"
                try:
                    error_data = e.response.json()
                    if 'error' in error_data and 'message' in error_data['error']:
                        error_msg = f"API错误: {error_data['error']['message']}"
                except Exception:
                    error_msg = f"HTTP错误: {e.response.status_code}, 内容: {e.response.text[:200]}"
                
                logger.error(f"API调用失败: {error_msg}")
                raise openai.APIError(error_msg)
                
            except httpx.RequestError as e:
                # 请求错误
                error_msg = f"请求错误: {str(e)}"
                logger.error(f"API调用失败: {error_msg}")
                raise openai.APIConnectionError(error_msg)
                
            except Exception as e:
                # 其他错误
                error_msg = f"API调用异常: {str(e)}"
                logger.error(f"API调用失败: {error_msg}")
                raise openai.APIError(error_msg) 