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
from app.utils.field_mapper import FieldMapper

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
    
    # 检查版本是否>=1.8.0（支持更多模型的response_format参数）
    supports_response_format = False
    try:
        if is_new_openai_sdk:
            version_parts = openai_version.split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1]) if len(version_parts) > 1 else 0
            supports_response_format = (major > 1) or (major == 1 and minor >= 8)
            logging.info(f"OpenAI SDK版本 {openai_version}, 是否支持response_format: {supports_response_format}")
    except Exception as e:
        logging.warning(f"无法检查OpenAI SDK版本详情: {str(e)}")
        supports_response_format = False
    
    if is_new_openai_sdk:
        from openai import OpenAI
        logging.info(f"使用OpenAI新版SDK: {openai_version}")
    else:
        logging.info(f"使用OpenAI旧版SDK: {openai_version}")
        
except ImportError:
    logging.error("未安装OpenAI SDK，请执行 pip install openai")
    is_new_openai_sdk = False
    supports_response_format = False

# 配置日志
logger = logging.getLogger(__name__)

class DeepseekClient(BaseAPIClient):
    """Deepseek AI客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, verify_ssl: bool = True):
        """
        初始化DeepSeek API客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            verify_ssl: 是否验证SSL证书
        """
        # 设置基本属性，确保在调用父类方法前已定义
        self.model = model or ""  # 确保model一定有值
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.debug_mode = bool(os.environ.get('DEBUG_MODE', False))
        
        # 初始化字段映射器
        from app.utils.field_mapper import FieldMapper
        self.field_mapper = FieldMapper()
        self.logger.info("初始化DeepSeek客户端和字段映射器")
        
        # 调用父类初始化方法 - 该方法会调用_load_config_from_env
        super().__init__(api_key=api_key, base_url=base_url, verify_ssl=verify_ssl)
        
        # 在父类初始化之后执行额外的初始化操作
        # 检查是否使用了不支持JSON输出的模型
        if self.model and "reasoner" in self.model.lower():
            logger.warning(f"注意: {self.model} 模型不支持JSON输出格式，这可能会影响批改结果的解析")
        
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
                # 修改：将verify_ssl参数传递给OpenAI客户端
                self.openai_client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                    http_client=httpx.Client(verify=self.verify_ssl)
                )
                logger.info(f"已初始化新版OpenAI客户端，SSL验证: {self.verify_ssl}")
            else:
                # 设置OpenAI全局配置
                openai.api_key = self.api_key
                openai.api_base = self.api_base
                # 在旧版SDK中没有直接设置verify_ssl的方法，记录警告
                logger.info("已设置旧版OpenAI全局配置")
                if not self.verify_ssl:
                    logger.warning("旧版OpenAI SDK不支持直接禁用SSL验证")
        except Exception as e:
            logger.error(f"初始化OpenAI客户端失败: {str(e)}")
            if not self.verify_ssl:
                logger.error("注意：您尝试禁用SSL验证，但在初始化客户端时仍然失败")
            
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
        
        # JSON输出格式支持状态
        self.supports_json_output = "reasoner" not in self.model.lower()
        if not self.supports_json_output:
            logger.warning(f"当前模型 {self.model} 不支持JSON输出格式，这可能会影响批改结果的解析准确性")
        
        logger.info(f"DeepSeek客户端初始化完成，使用模型: {self.model}, 支持JSON输出: {self.supports_json_output}")
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return "deepseek"
    
    def safe_parse_json(self, response_text: Union[str, Dict, None]) -> Optional[Dict]:
        """
        安全解析JSON响应，处理各种JSON格式问题
        
        Args:
            response_text: 可能包含JSON的文本或已是字典的响应
            
        Returns:
            Optional[Dict]: 解析后的JSON对象，解析失败则返回None
        """
        # 检查空响应
        if not response_text:
            logger.warning("收到空响应")
            return None
            
        # 如果已经是字典，直接返回
        if isinstance(response_text, dict):
            return response_text
            
        # 清理JSON字符串并尝试解析
        try:
            # 去除可能导致问题的字符
            cleaned_text = self._clean_json(response_text)
            
            # 尝试直接解析
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.debug(f"直接JSON解析失败: {str(e)}")
            
            # 尝试提取最外层的JSON对象
            json_pattern = r'({[\s\S]*?})'
            matches = re.findall(json_pattern, cleaned_text)
            
            if matches:
                for potential_json in matches:
                    try:
                        # 尝试解析每个匹配项
                        result = json.loads(potential_json)
                        if isinstance(result, dict):
                            logger.debug("成功从文本中提取JSON对象")
                            return result
                    except json.JSONDecodeError:
                        continue
                        
            # 最后尝试使用eval (确保只包含有效的JSON字符)
            if all(c in '{}[](),:."\'0123456789truefalsenullabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_- \n\t\r' for c in cleaned_text):
                try:
                    # 将json关键字转换为Python兼容形式
                    cleaned_text = cleaned_text.replace('null', 'None')
                    cleaned_text = cleaned_text.replace('true', 'True')
                    cleaned_text = cleaned_text.replace('false', 'False')
                    
                    result = eval(cleaned_text)
                    if isinstance(result, dict):
                        logger.warning("使用eval解析JSON成功，但这不是推荐的方法")
                        return result
                except Exception as e:
                    logger.warning(f"使用eval解析失败: {str(e)}")
            
            logger.warning(f"所有JSON解析方法均失败，返回None。原始文本: {response_text[:100]}...")
            return None
            
        except Exception as e:
            logger.error(f"安全解析JSON时出错: {str(e)}")
            return None
    
    def _clean_json(self, text: str) -> str:
        """
        清理JSON字符串，提取代码块并移除不相关字符
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            str: 清理后的JSON字符串
        """
        # 移除Unicode字符BOM和其他不可见字符
        text = text.strip()
        
        # 尝试从markdown代码块中提取
        code_block_pattern = r'```(?:json)?(.*?)```'
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        if matches:
            # 提取最后一个代码块(如果存在多个)
            extracted_text = matches[-1].strip()
            logger.debug("从代码块中提取到潜在的JSON文本")
            return extracted_text
            
        # 如果没有代码块，尝试查找JSON块
        json_block_start = text.find('{')
        json_block_end = text.rfind('}')
        
        if json_block_start >= 0 and json_block_end > json_block_start:
            extracted_text = text[json_block_start:json_block_end+1]
            logger.debug("提取了可能的JSON块")
            return extracted_text
            
        # 如果没有找到明确的JSON标记，返回原始文本
        return text
    
    def _extract_result(self, response_text: str) -> Dict[str, Any]:
        """
        从API响应中提取格式化的结果
        
        Args:
            response_text: API响应文本
            
        Returns:
            Dict: 包含评分结果的字典，使用标准化字段结构
        """
        try:
            # 从响应中提取JSON字符串
            self.logger.debug(f"提取结果 - 响应长度: {len(response_text)}")
            
            # 保留原始响应用于调试
            original_response = None
            if isinstance(response_text, str) and len(response_text) < 1000:
                original_response = response_text
            
            # 解析JSON响应
            parsed_json = self.safe_parse_json(response_text)
            if not parsed_json:
                self.logger.error("无法解析响应JSON")
                return {}
                
            # 使用字段映射器标准化结果
            self.logger.debug(f"开始字段标准化，原始字段: {list(parsed_json.keys())}")
            normalized = self.field_mapper.normalize_result(parsed_json, "deepseek")
            
            # 保留原始响应以便调试
            if original_response:
                normalized["_original_response"] = original_response
                
            # 保留原始解析结果供参考
            normalized["_raw_data"] = parsed_json
                
            self.logger.debug(f"标准化结果完成: {normalized.keys()}")
            
            # 返回标准化结果
            return normalized
            
        except Exception as e:
            self.logger.exception(f"提取结果时出错: {str(e)}")
            return {}
    
    def format_response(self, response: Dict) -> Dict[str, Any]:
        """
        格式化API响应，检查分数是否有效
        
        Args:
            response: API响应数据
            
        Returns:
            Dict: 格式化后的响应
        """
        self.logger.debug(f"格式化API响应，keys: {list(response.keys())}")
        
        # 检查是否有 scores 字段和 total 值
        if "scores" in response and "total" in response["scores"]:
            total_score = response["scores"]["total"]
            self.logger.debug(f"从标准化字段结构中获取到总分: {total_score}")
            
            # 如果总分为空或无效，设置为0
            if total_score is None or not isinstance(total_score, (int, float)):
                self.logger.warning(f"无效的总分值: {total_score}，设置为0")
                response["scores"]["total"] = 0
            
            # 将总分限制在有效范围内 (0-50)
            elif total_score < 0 or total_score > 50:
                old_score = total_score
                response["scores"]["total"] = max(0, min(50, total_score))
                self.logger.warning(f"总分超出有效范围 ({old_score})，已调整为: {response['scores']['total']}")
            
            # 为向后兼容添加 total_score 字段
            response["total_score"] = response["scores"]["total"]
        
        # 向后兼容检查，处理旧格式的响应
        elif "total_score" in response:
            total_score = response["total_score"]
            self.logger.debug(f"从旧字段结构中获取到总分: {total_score}")
            
            # 如果总分为空或无效，设置为0
            if total_score is None or not isinstance(total_score, (int, float)):
                self.logger.warning(f"无效的总分值: {total_score}，设置为0")
                response["total_score"] = 0
            
            # 将总分限制在有效范围内 (0-50)
            elif total_score < 0 or total_score > 50:
                old_score = total_score
                response["total_score"] = max(0, min(50, total_score))
                self.logger.warning(f"总分超出有效范围 ({old_score})，已调整为: {response['total_score']}")
            
            # 为新格式添加 scores 字段
            if "scores" not in response:
                response["scores"] = {"total": response["total_score"]}
        
        # 如果没有找到总分，返回错误结果
        else:
            self.logger.error("响应中缺少总分字段")
            error_msg = "响应中缺少总分字段"
            response = self._create_default_result(error_msg)
            
        return response
    
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
                
                # 使用字典传递参数，根据模型决定是否添加response_format参数
                api_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,  # 使用较低的温度以获得更一致的结果
                    "max_tokens": 4000,  # 为详细的批改结果提供足够的token
                    "timeout": 60,  # 设置60秒超时
                }
                
                # 只有当SDK版本支持且模型不是reasoner时，才添加response_format参数
                global supports_response_format, openai_version
                can_use_json_format = supports_response_format and "reasoner" not in self.model.lower()
                
                if can_use_json_format:
                    logger.info(f"SDK版本{openai_version}支持JSON输出，当前模型{self.model}也支持，添加response_format参数")
                    api_params["response_format"] = {"type": "json_object"}
                else:
                    if "reasoner" in self.model.lower():
                        logger.info(f"当前模型{self.model}不支持JSON输出格式，使用普通输出")
                    elif not supports_response_format:
                        logger.info(f"当前SDK版本{openai_version}不支持response_format参数，使用普通输出")
                
                response = self.openai_client.chat.completions.create(**api_params)
                
                # 提取结果前做防御性检查
                api_response = response.model_dump()
                logger.debug(f"API响应类型: {type(api_response)}")
                
                # 从API响应中安全地提取内容
                if isinstance(api_response, dict) and "choices" in api_response and api_response["choices"]:
                    try:
                        content = api_response["choices"][0]["message"]["content"]
                        logger.debug(f"从API响应中提取到内容: {content[:100]}...")
                        correction_result = self._extract_result(content)
                    except (KeyError, TypeError, IndexError) as e:
                        logger.warning(f"从API响应中提取内容失败: {str(e)}，尝试使用完整响应")
                        correction_result = self._extract_result(api_response)
                else:
                    logger.warning("API响应格式异常，尝试使用完整响应")
                    correction_result = self._extract_result(api_response)
                
                # 校验结果格式
                valid_result = False
                
                # 检查分数是否有效
                if "scores" in correction_result and "total" in correction_result["scores"] and correction_result["scores"]["total"] > 0:
                    valid_result = True
                    logger.info(f"成功提取评分结果，总分: {correction_result['scores']['total']}")
                # 向后兼容旧字段
                elif correction_result.get("total_score", 0) > 0:
                    valid_result = True
                    logger.info(f"成功提取评分结果(旧格式)，总分: {correction_result['total_score']}")
                    # 为了保持一致性，添加scores字段
                    if "scores" not in correction_result:
                        correction_result["scores"] = {"total": correction_result["total_score"]}
                # 检查中文响应
                elif "raw_data" in correction_result and isinstance(correction_result["raw_data"], dict):
                    # 尝试从原始数据中提取分数
                    raw_data = correction_result["raw_data"]
                    if "总得分" in raw_data:
                        try:
                            score = float(raw_data["总得分"])
                            # 更新标准化结构
                            correction_result["scores"] = correction_result.get("scores", {})
                            correction_result["scores"]["total"] = score
                            correction_result["total_score"] = score  # 添加兼容字段
                            valid_result = True
                            logger.info(f"从原始数据提取到总分: {score}")
                        except (ValueError, TypeError):
                            logger.warning("无法转换原始总分")
                
                if valid_result:
                    # 确保返回的结果经过格式化处理，规范化分数范围
                    formatted_result = self.format_response(correction_result)
                    return {
                        "status": "success",
                        "result": formatted_result
                    }
                else:
                    error_msg = "API返回的结果格式无效或未包含有效分数"
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
        # 修改系统提示词，强调JSON格式输出
        system_prompt = """你是专业的中文作文批改老师，擅长分析文章结构、内容、语言和表达，能够提供详尽的评价和建议。
请对以下作文进行详细批改。

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

请严格按照以下JSON格式输出评分结果，不要包含任何额外的文字或解释：

{
    "总得分": 45,
    "分项得分": {
        "内容主旨": 18,
        "语言文采": 14,
        "文章结构": 9,
        "文面书写": 4
    },
    "总体评价": "这是一篇内容充实的文章，请在这里提供200字左右的总体评价。",
    "内容分析": "文章主题明确，论述有力，请在这里提供200字左右的内容分析。",
    "语言分析": "语言表达流畅，用词准确，请在这里提供200字左右的语言分析。",
    "结构分析": "文章结构合理，层次分明，请在这里提供200字左右的结构分析。",
    "写作建议": "建议在论述方面更加深入，请在这里提供200字左右的写作建议。",
    "错别字": ["错误1->正确1", "错误2->正确2"]
}

你的回复必须是一个有效的JSON对象，只输出JSON内容，不要有任何其他文字。请确保所有键名使用双引号，数值不使用引号，并确保总分和分项得分都是数字。"""

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
                # 将类型指导加到修改后的 Prompt 之前
                system_prompt = essay_type_guides[essay_type] + "\n\n" + system_prompt
            else:
                logger.warning(f"未识别的作文类型: {essay_type}")
        
        # 构造用户消息
        user_message = ""
        if title:
            user_message += f"标题：{title}\n\n"
        
        if prompt:
            user_message += f"写作提示：{prompt}\n\n"
        
        user_message += f"作文内容：\n{content}"
        
        # 添加字数信息
        text_length = len(content)
        user_message += f"\n\n字数：{text_length}字"
        
        # 构造消息列表
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        logger.debug(f"已准备批改消息 (JSON格式优化Prompt)，系统提示词长度: {len(system_prompt)}字，用户消息长度: {len(user_message)}字")
        
        return messages
        
    def _validate_correction_result_format(self, result: Dict) -> bool:
        """
        验证批改结果的格式是否有效
        
        Args:
            result: 批改结果
            
        Returns:
            bool: 格式是否有效
        """
        # 首先检查原始数据中的中文字段
        if "_raw_data" in result and isinstance(result["_raw_data"], dict):
            raw_data = result["_raw_data"]
            if "总得分" in raw_data:
                try:
                    score = float(raw_data["总得分"])
                    if 0 <= score <= 50:
                        logger.debug(f"通过原始数据中的总得分验证成功: {score}")
                        return True
                except (ValueError, TypeError) as e:
                    logger.warning(f"原始数据中的总得分无效: {raw_data['总得分']}, 错误: {str(e)}")
                    # 继续检查其他格式
        
        # 检查标准化字段结构
        if "scores" in result and isinstance(result["scores"], dict) and "total" in result["scores"]:
            logger.debug("使用标准化字段结构验证结果")
            try:
                score = float(result["scores"]["total"])
                # 验证分数范围 (允许0-50的标准化范围)
                if not (0 <= score <= 50):
                    logger.warning(f"标准化总分超出合理范围(0-50): {score}")
                    return False
                logger.debug(f"标准化结果验证通过，总分: {score}")
                return True
            except (ValueError, TypeError) as e:
                logger.warning(f"标准化总分不是有效数字: {result['scores'].get('total')}, 错误: {str(e)}")
                # 继续检查旧格式字段
        
        # 向后兼容检查 - 支持中英文字段名
        logger.debug("尝试使用旧格式字段验证结果")
        required_fields_en = ["total_score"]
        required_fields_cn = ["总得分"]
        
        # 验证中英文字段中至少有一组字段是完整的
        en_fields_present = all(field in result for field in required_fields_en)
        cn_fields_present = all(field in result for field in required_fields_cn)
        
        # 如果两种格式都不完整，记录警告并返回失败
        if not (en_fields_present or cn_fields_present):
            logger.warning(f"批改结果缺少必要字段: total_score 或 总得分")
            return False
                
        # 检查总分是否为数字且在合理范围内
        try:
            # 尝试获取中文或英文的分数字段
            score = None
            if "总得分" in result:
                score = float(result["总得分"])
                # 中文结果使用0-50的范围
                if not (0 <= score <= 50):
                    logger.warning(f"中文总得分超出合理范围(0-50): {score}")
                    return False
            elif "total_score" in result:
                score = float(result["total_score"])
                # 英文结果使用0-50的范围
                if not (0 <= score <= 50):
                    logger.warning(f"英文total_score超出合理范围(0-50): {score}")
                    return False
            
            if score is None:
                logger.warning(f"未找到有效的分数字段")
                return False
                
            logger.debug(f"旧格式结果验证通过，总分: {score}")
            return True
            
        except (ValueError, TypeError) as e:
            score_field = "总得分" if "总得分" in result else "total_score"
            logger.warning(f"总得分不是有效数字: {result.get(score_field)}, 错误: {str(e)}")
            return False
        
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
        
        # 只有当SDK版本支持且模型不是reasoner时，才添加response_format参数
        global supports_response_format, openai_version
        can_use_json_format = supports_response_format and "reasoner" not in self.model.lower()
        
        if can_use_json_format:
            logger.info(f"异步调用 - SDK版本{openai_version}支持JSON输出，当前模型{self.model}也支持，添加response_format参数")
            data["response_format"] = {"type": "json_object"}
        else:
            if "reasoner" in self.model.lower():
                logger.info(f"异步调用 - 当前模型{self.model}不支持JSON输出格式，使用普通输出")
            elif not supports_response_format:
                logger.info(f"异步调用 - 当前SDK版本{openai_version}不支持response_format参数，使用普通输出")
        
        # 添加其他参数
        for key, value in kwargs.items():
            if key != 'response_format':  # response_format已经处理，避免覆盖
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
                
                # 记录完整响应以便调试
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"异步API完整响应: {json.dumps(result, ensure_ascii=False)[:500]}...")
                
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

    def _create_default_result(self, error_message: str = None) -> Dict[str, Any]:
        """
        创建默认的结果对象，用于API调用失败时返回
        
        Args:
            error_message: 错误信息
            
        Returns:
            Dict: 包含默认值的结果对象，使用标准化字段结构
        """
        # 标准化字段结构的默认结果
        default_result = {
            "scores": {
                "total": 0,
                "dimensions": {
                    "content": 0,
                    "language": 0,
                    "structure": 0,
                    "grammar": 0
                }
            },
            "analyses": {
                "summary": error_message or "评分失败，请查看日志了解详情",
                "content": "",
                "language": "",
                "structure": ""
            },
            "feedback": {
                "strengths": [],
                "weaknesses": [],
                "improvements": [],
                "corrections": []
            },
            "metadata": {
                "provider": "deepseek",
                "model": self.model,
                "processing_time": 0,
                "error": True,
                "error_message": error_message
            }
        }
        
        logger.debug(f"已创建标准化默认结果对象")
        return default_result
        
    def _create_empty_result(self, error_message: str = None, essay_content: str = None) -> Dict[str, Any]:
        """
        创建空结果对象，用于异步API调用失败时返回
        
        Args:
            error_message: 错误信息
            essay_content: 作文内容
            
        Returns:
            Dict: 包含默认值和错误信息的结果对象，使用标准化字段结构
        """
        # 复用默认结果创建方法
        result = self._create_default_result(error_message)
        
        # 更新元数据
        result["metadata"].update({
            "timestamp": datetime.now().isoformat(),
            "async": True,
            "content_length": len(essay_content) if essay_content else 0
        })
        
        # 添加简短错误摘要到分析结果中
        result["analyses"]["summary"] = f"错误: {error_message}" if error_message else "未知错误导致评分失败"
        
        return result 

    def validate_content(self, content: str) -> None:
        """
        验证作文内容的有效性
        
        Args:
            content: 作文内容
            
        Raises:
            ValueError: 内容无效时抛出
        """
        if not content or not isinstance(content, str):
            raise ValueError("作文内容不能为空且必须是字符串")
            
        if len(content) < 10:
            raise ValueError(f"作文内容过短 ({len(content)}字)，至少需要10个字符")
            
        # 可以添加更多的验证逻辑
        return

    def _load_config_from_env(self):
        """从环境变量和配置加载配置"""
        # 首先调用父类方法
        super()._load_config_from_env()
        
        # 额外处理模型配置
        config_model = AI_CONFIG.get('MODEL', "")
        env_model = os.environ.get("DEEPSEEK_MODEL", "")
        
        # 只有当model为空时才从环境变量或配置加载
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
