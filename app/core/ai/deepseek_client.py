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
import requests

from app.core.ai.api_client import BaseAPIClient, APIError
from config.ai_config import AI_CONFIG

# 导入OpenAI SDK
try:
    from openai import OpenAI
except ImportError:
    logging.error("未安装OpenAI SDK，请执行 pip install openai")

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
        
        # 初始化OpenAI客户端，正确传递参数
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base.replace('/v1', ''),  # 移除基础URL中的/v1，SDK会自动添加
            timeout=60.0,
            max_retries=3
        )
        
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
        import re
        # 移除控制字符和其他可能导致JSON解析错误的字符
        return re.sub(r'[\x00-\x1F\x7F]', '', json_str)

    def analyze_essay(self, content: str) -> Dict[str, Any]:
        """
        使用Deepseek分析作文
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 分析结果
        """
        try:
            logger.info(f"使用Deepseek分析作文，内容长度: {len(content)}")
            text_length = len(content)
            
            # 使用原始50分制评分标准
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

字数：{text_length}字

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
            
            try:
                # 使用OpenAI SDK调用DeepSeek API
                logger.info(f"准备调用DeepSeek API，模型: {self.model}, URL: {self.api_base}")
                logger.info(f"API请求路径: {self.api_base}/chat/completions")
                
                try:
                    # 记录请求参数
                    logger.info(f"请求参数: model={self.model}, temperature=0.1, max_tokens=2048, top_p=0.8")
                    logger.info(f"消息数量: {len(messages)}")
                    
                    # 根据官方文档，调用DeepSeek API (与OpenAI兼容格式)
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=2048,
                        top_p=0.8
                    )
                    logger.info(f"DeepSeek API调用成功，响应ID: {response.id if hasattr(response, 'id') else 'unknown'}")
                    
                except Exception as api_err:
                    logger.error(f"DeepSeek API调用出错: {str(api_err)}")
                    # 增强错误日志
                    logger.error(f"""
                    API请求失败详情：
                    URL: {self.api_base}/chat/completions
                    模型: {self.model}
                    消息长度: {len(content)}
                    """)
                    
                    error_details = ""
                    
                    # 提取并记录详细错误信息
                    if hasattr(api_err, 'response') and api_err.response:
                        status_code = getattr(api_err.response, 'status_code', 'unknown')
                        error_text = getattr(api_err.response, 'text', '')[:500]
                        logger.error(f"响应状态码: {status_code}")
                        logger.error(f"响应内容: {error_text}")
                        error_details = f"状态码: {status_code}, 响应: {error_text[:100]}"
                    
                    raise APIError(f"DeepSeek API调用失败: {str(api_err)} {error_details}")
                
                # 提取响应内容
                if response and hasattr(response, 'choices') and len(response.choices) > 0:
                    try:
                        # 提取内容并解析JSON
                        content = response.choices[0].message.content
                        logger.info(f"DeepSeek API响应内容: {content[:100]}...")
                        result_json = json.loads(content)
                        return self.format_response(result_json)
                    except json.JSONDecodeError:
                        # 尝试从文本中提取JSON，并应用JSON清洗
                        text_content = response.choices[0].message.content
                        json_start = text_content.find('{')
                        json_end = text_content.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            # 应用JSON清洗函数
                            json_str = self._clean_json(text_content[json_start:json_end])
                            try:
                                result_json = json.loads(json_str)
                                logger.info("成功通过JSON清洗处理解析响应")
                                return self.format_response(result_json)
                            except json.JSONDecodeError as e:
                                logger.error(f"无法从文本中提取有效JSON: {str(e)}")
                                logger.error(f"清洗后的JSON内容: {json_str[:200]}...")
                        
                        return {
                            "status": "error",
                            "message": f"无法解析JSON响应"
                        }
                else:
                    logger.error(f"DeepSeek响应格式异常")
                    return {
                        "status": "error",
                        "message": "API响应格式错误"
                    }
                
            except Exception as e:
                logger.error(f"DeepSeek API请求错误: {str(e)}")
                return {
                    "status": "error",
                    "message": f"API请求错误: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"DeepSeek分析过程中发生错误: {str(e)}\n{traceback.format_exc()}")
            return {
                "status": "error", 
                "message": f"分析失败: {str(e)}"
            }
    
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
    
    def _extract_result(self, response: Dict) -> Dict[str, Any]:
        """
        从API响应中提取结果
        
        Args:
            response: API响应
            
        Returns:
            Dict: 提取的结果
        """
        try:
            # 提取分数 (保持50分制)
            total_score = response.get("总得分", 0)
            
            # 提取分项得分
            分项得分 = response.get("分项得分", {})
            content_score = 分项得分.get("内容主旨", 0)
            language_score = 分项得分.get("语言文采", 0)
            structure_score = 分项得分.get("文章结构", 0)
            writing_score = 分项得分.get("文面书写", 0)
            
            # 基于分数确定等级
            if total_score >= 43:
                level = "A"
            elif total_score >= 35:
                level = "B"
            elif total_score >= 27:
                level = "C"
            else:
                level = "D"
            
            # 提取评价和分析
            overall_assessment = response.get("总体评价", "")
            content_analysis = response.get("内容分析", "")
            language_analysis = response.get("语言分析", "")
            structure_analysis = response.get("结构分析", "")
            improvement_suggestions = response.get("写作建议", "")
            
            # 提取错别字
            spelling_errors = response.get("错别字", [])
            
            return {
                "total_score": total_score,
                "level": level,
                "content_score": content_score,
                "language_score": language_score,
                "structure_score": structure_score,
                "writing_score": writing_score,
                "overall_assessment": overall_assessment,
                "content_analysis": content_analysis,
                "language_analysis": language_analysis,
                "structure_analysis": structure_analysis,
                "improvement_suggestions": improvement_suggestions,
                "spelling_errors": {
                    "解析": spelling_errors
                }
            }
        except Exception as e:
            logger.error(f"提取Deepseek响应数据时发生错误: {str(e)}")
            raise Exception(f"提取响应数据失败: {str(e)}")

    def correct_essay(self, content: str) -> Dict[str, Any]:
        """
        批改作文并返回标准化结果
        
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
            logger.info(f"开始批改作文，内容长度: {len(content)}")
            
            # 使用analyze_essay获取分析结果
            analysis_result = self.analyze_essay(content)
            
            if analysis_result.get("status") == "success":
                # 获取原始结果
                raw_result = analysis_result.get("result", {})
                
                # 直接使用返回的结果，确保键名与期望匹配
                corrected_result = {
                    "总得分": raw_result.get("总得分", 0),
                    "分项得分": raw_result.get("分项得分", {
                        "内容主旨": 0,
                        "语言文采": 0,
                        "文章结构": 0,
                        "文面书写": 0
                    }),
                    "总体评价": raw_result.get("总体评价", ""),
                    "内容分析": raw_result.get("内容分析", ""),
                    "语言分析": raw_result.get("语言分析", ""),
                    "结构分析": raw_result.get("结构分析", ""),
                    "写作建议": raw_result.get("写作建议", ""),
                    "错别字": raw_result.get("错别字", [])
                }
                
                return {
                    "status": "success",
                    "result": corrected_result
                }
            else:
                # 保留错误信息
                return analysis_result
                
        except Exception as e:
            logger.error(f"批改作文失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"批改作文失败: {str(e)}"
            } 