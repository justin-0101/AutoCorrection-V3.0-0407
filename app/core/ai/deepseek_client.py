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
        
        # 初始化OpenAI客户端，设置合理的超时和重试参数
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base.replace('/v1', ''),  # 移除基础URL中的/v1，SDK会自动添加
            timeout=60.0,  # 增加超时时间到60秒
            max_retries=5,  # 保持5次重试
            default_headers={"Keep-Alive": "timeout=60, max=1000"}  # 增加keep-alive超时
        )
        
        # API调用配置
        self.api_config = {
            'timeout': httpx.Timeout(
                connect=5.0,    # 增加连接超时
                read=60.0,      # 增加读取超时到60秒
                write=20.0,     # 增加写入超时
                pool=10.0       # 增加连接池超时
            ),
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
        
        # 移除JSON前后可能的说明文字
        json_str = re.sub(r'^[^{]*', '', json_str)
        json_str = re.sub(r'[^}]*$', '', json_str)
        
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
    
    def _extract_result(self, response: Dict) -> Dict:
        """
        从API响应中提取结果数据并格式化
        
        Args:
            response: API响应
            
        Returns:
            Dict: 格式化后的结果
        """
        try:
            # 首先从API响应中提取内容
            content = None
            
            if response and 'choices' in response and len(response['choices']) > 0:
                choice = response['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    content = choice['message']['content']
            
            if not content:
                logger.error("API响应中未找到有效内容")
                logger.debug(f"API响应: {json.dumps(response, ensure_ascii=False)}")
                return {"error": "无法从API响应中获取内容"}
            
            # 尝试解析JSON
            try:
                # 清理可能包含的非JSON内容
                content = self._clean_json(content)
                json_result = json.loads(content)
                logger.debug(f"成功解析JSON: {json.dumps(json_result, ensure_ascii=False)}")
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON解析错误: {str(json_err)}")
                logger.error(f"原始内容: {content}")
                
                # 尝试使用正则表达式提取JSON部分
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
                if json_match:
                    try:
                        json_content = json_match.group(1)
                        logger.debug(f"从Markdown代码块中提取JSON: {json_content}")
                        json_result = json.loads(json_content)
                    except json.JSONDecodeError:
                        logger.error("从Markdown代码块中提取的JSON解析失败")
                        # 如果还是失败，返回预设结构但值为空的结果
                        return self._create_empty_result()
                else:
                    logger.error("无法在响应中找到JSON格式内容")
                    return self._create_empty_result()
            
            # 提取分数 (保持50分制)
            total_score = json_result.get("总得分", 0)
            
            # 提取分项得分
            分项得分 = json_result.get("分项得分", {})
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
            overall_assessment = json_result.get("总体评价", "")
            content_analysis = json_result.get("内容分析", "")
            language_analysis = json_result.get("语言分析", "")
            structure_analysis = json_result.get("结构分析", "")
            improvement_suggestions = json_result.get("写作建议", "")
            
            # 提取错别字
            spelling_errors = json_result.get("错别字", [])
            
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
        except Exception as e:
            logger.error(f"提取Deepseek响应数据时发生错误: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return self._create_empty_result(error=str(e))
    
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError)),
        retry_error_callback=lambda retry_state: {
            "status": "error",
            "message": f"API调用失败，已重试{retry_state.attempt_number}次"
        }
    )
    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> Dict:
        """
        调用API并处理响应
        
        Args:
            messages: 消息列表
            
        Returns:
            Dict: API响应
            
        Raises:
            APIError: API调用错误
        """
        try:
            print(f"[DeepseekClient] 开始API调用，消息数: {len(messages)}")
            logger.info(f"[DeepseekClient] 开始API调用，消息数: {len(messages)}")
            
            # 记录API请求配置
            api_config = {
                "url": self.api_url,
                "model": self.model,
                "temperature": self.api_config.get("temperature", 0.1),
                "timeout": self.timeout
            }
            print(f"[DeepseekClient] API配置: {api_config}")
            logger.info(f"[DeepseekClient] API配置: {api_config}")
            
            # 发起API请求
            print(f"[DeepseekClient] 发送请求到 {self.api_url}")
            
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
            
            # 调用API
            response = await self.client.chat.completions.create(**request_params)
            
            # API请求结束时间和耗时
            api_end_time = datetime.now()
            api_elapsed = (api_end_time - api_start_time).total_seconds()
            
            # 打印请求后的时间戳和耗时
            print(f"[DeepseekClient] 收到API响应时间: {api_end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            print(f"[DeepseekClient] API请求总耗时: {api_elapsed:.2f}秒")
            
            # 格式化响应
            formatted_response = self.format_response(response)
            
            # 打印响应摘要
            content_length = len(formatted_response.get("content", ""))
            print(f"[DeepseekClient] API响应内容长度: {content_length}字符")
            
            return formatted_response
            
        except httpx.RequestError as e:
            print(f"[DeepseekClient] API请求错误: {str(e)}")
            logger.error(f"[DeepseekClient] API请求错误: {str(e)}")
            raise APIError(f"API请求错误: {str(e)}")
            
        except httpx.HTTPStatusError as e:
            print(f"[DeepseekClient] API状态错误: {e.response.status_code} - {str(e)}")
            logger.error(f"[DeepseekClient] API状态错误: {e.response.status_code} - {str(e)}")
            raise APIError(f"API状态错误: {e.response.status_code} - {str(e)}")
            
        except json.JSONDecodeError as e:
            print(f"[DeepseekClient] JSON解析错误: {str(e)}")
            logger.error(f"[DeepseekClient] JSON解析错误: {str(e)}")
            raise APIError(f"JSON解析错误: {str(e)}")
            
        except Exception as e:
            print(f"[DeepseekClient] API调用异常: {str(e)}")
            logger.error(f"[DeepseekClient] API调用异常: {str(e)}")
            logger.error(f"[DeepseekClient] 异常详情: {traceback.format_exc()}")
            raise APIError(f"API调用异常: {str(e)}")

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
            print(f"[DeepseekClient] 开始批改作文，内容长度: {len(content)}")
            logger.info(f"[DeepseekClient] 开始批改作文，内容长度: {len(content)}")
            
            # 计算预估token数（中文每个字约2-3个token）
            estimated_tokens = len(content) * 3
            
            # 如果预估token数超过限制，分块处理
            if estimated_tokens > self.api_config['chunk_size']:
                print(f"[DeepseekClient] 内容较长，将分块处理，预估token数: {estimated_tokens}")
                logger.info(f"[DeepseekClient] 内容较长，将分块处理，预估token数: {estimated_tokens}")
                return self._process_long_content(content)
            
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
            
            # 记录开始时间
            start_time = datetime.now()
            
            # 使用异步调用并等待结果
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(self._call_api(messages))
            
            # 计算耗时
            elapsed_time = (datetime.now() - start_time).total_seconds()
            print(f"[DeepseekClient] API调用完成，耗时: {elapsed_time:.2f}秒")
            logger.info(f"[DeepseekClient] API调用完成，耗时: {elapsed_time:.2f}秒")
            
            # 提取结果
            result = self._extract_result(response)
            
            # 记录结果概要
            total_score = result.get('total_score', 'N/A')
            print(f"[DeepseekClient] 批改结果: 总分={total_score}")
            logger.info(f"[DeepseekClient] 批改结果: 总分={total_score}")
            
            return {
                "status": "success",
                "result": result
            }
            
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

    async def correct_essay_async(self, content: str) -> Dict[str, Any]:
        """异步批改作文"""
        try:
            logger.info(f"异步批改作文，内容长度: {len(content)}")
            
            # 计算预估token数
            estimated_tokens = len(content) * 3
            
            # 如果预估token数超过限制，分块处理
            if estimated_tokens > self.api_config['chunk_size']:
                logger.info(f"内容较长，将分块处理，预估token数: {estimated_tokens}")
                return await self._process_long_content_async(content)
            
            system_prompt = f"""你是一位专业的语文教师，现在需要你按照广东中考语文作文评分标准对一篇作文进行全面评分和详细分析。
            // ... existing prompt ...
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            
            response = await self._call_api(messages)
            result = self._extract_result(response)
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"异步批改作文失败: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"异步批改作文失败: {str(e)}"
            }

    async def _process_long_content_async(self, content: str) -> Dict[str, Any]:
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
            logger.error(f"处理长文本失败: {str(e)}")
            return {
                "status": "error",
                "message": f"处理长文本失败: {str(e)}"
            } 