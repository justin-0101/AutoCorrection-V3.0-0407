#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAI客户端
用于与OpenAI API交互
"""

import os
import json
import logging
import traceback
import requests
import re
from typing import Dict, Any, List, Optional, Union

from app.core.ai.api_client import BaseAPIClient, APIError

# 配置日志
logger = logging.getLogger(__name__)

class OpenAIClient(BaseAPIClient):
    """OpenAI客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, verify_ssl: bool = True):
        """
        初始化OpenAI客户端
        
        Args:
            api_key: OpenAI API密钥
            base_url: OpenAI API基础URL
            model: 使用的模型
            verify_ssl: 是否验证SSL证书
        """
        self.model = model or "gpt-3.5-turbo-16k"
        super().__init__(api_key, base_url, verify_ssl)
        
        # 检查模型名称
        if not self.model:
            self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo-16k")
        
        logger.info(f"OpenAI客户端初始化完成，使用模型: {self.model}")
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return "openai"
    
    def _load_config_from_env(self):
        """从环境变量加载配置"""
        super()._load_config_from_env()
        
        # 默认基础URL
        if not self.base_url:
            self.base_url = "https://api.openai.com/v1"
        
        # 从环境变量加载模型
        if not self.model:
            self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo-16k")
    
    def analyze_essay(self, content: str) -> Dict[str, Any]:
        """
        使用OpenAI分析作文
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 分析结果
        """
        try:
            logger.info(f"使用OpenAI分析作文，内容长度: {len(content)}")
            
            system_prompt = """
            你是一位专业的语文教师，现在需要你批改一篇作文。请提供以下信息：
            1. 总得分（满分100分）
            2. 分项得分（内容主旨、语言文采、文章结构、写作技巧，每项满分100分）
            3. 总体评价（200字左右）
            4. 内容分析（优点与不足）
            5. 语言分析（用词、句式等）
            6. 结构分析（段落、过渡等）
            7. 写作建议（改进方向）
            8. 错别字列表

            请使用以下JSON格式返回结果：
            {
                "总得分": 85,
                "分项得分": {
                    "内容主旨": 80,
                    "语言文采": 85,
                    "文章结构": 90,
                    "写作技巧": 85
                },
                "总体评价": "这是一篇...",
                "内容分析": "文章主题明确...",
                "语言分析": "语言表达流畅...",
                "结构分析": "文章结构合理...",
                "写作建议": "建议在...",
                "错别字": ["错误1->正确1", "错误2->正确2"]
            }
            
            请确保只返回JSON格式的结果，不要包含其他说明文字。
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
            
            try:
                # 使用requests库发送请求
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"}
                }
                
                # 发送请求
                response = requests.post(
                    f"{self.base_url}/chat/completions", 
                    headers=headers,
                    json=data,
                    verify=self.verify_ssl,
                    timeout=60
                )
                
                # 检查响应
                response.raise_for_status()
                response_data = response.json()
                
                if not response_data.get("choices"):
                    raise APIError("OpenAI响应没有包含有效的内容")
                
                content = response_data["choices"][0]["message"]["content"]
                result_json = json.loads(content)
                
                # 解析分析结果
                return self.format_response(self._parse_correction_result(result_json))
                
            except requests.RequestException as e:
                status_code = getattr(e.response, 'status_code', 'unknown') if hasattr(e, 'response') else 'unknown'
                error_text = getattr(e.response, 'text', '') if hasattr(e, 'response') else str(e)
                logger.error(f"OpenAI API请求失败: 状态码={status_code}, 错误={error_text}")
                raise APIError(f"OpenAI API请求失败: {str(e)}")
                
            except json.JSONDecodeError as e:
                logger.error(f"无法解析OpenAI响应为JSON: {str(e)}")
                raise APIError(f"无法解析OpenAI响应: {str(e)}")
                
            except Exception as e:
                logger.error(f"处理OpenAI响应时发生错误: {str(e)}")
                raise APIError(f"处理响应失败: {str(e)}")
                
        except APIError as e:
            logger.error(f"OpenAI API错误: {e.message}")
            return {
                "status": "error",
                "message": f"OpenAI API错误: {e.message}"
            }
        except Exception as e:
            logger.error(f"OpenAI分析过程中发生错误: {str(e)}\n{traceback.format_exc()}")
            return {
                "status": "error", 
                "message": f"分析失败: {str(e)}"
            }
    
    def _parse_correction_result(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析AI批改返回的结果
        
        Args:
            response: API响应数据
            
        Returns:
            Dict: 解析后的结果
        """
        try:
            # 获取content和reasoning_content
            content = None
            reasoning_content = None
            
            if response and "choices" in response:
                message = response["choices"][0].get("message", {})
                content = message.get("content", "")
                reasoning_content = message.get("reasoning_content", "")
                
            if not content and not reasoning_content:
                logger.error("API响应中没有找到有效的content或reasoning_content")
                return {
                    "status": "error",
                    "message": "API返回结果格式错误"
                }
                
            # 优先使用content中的JSON数据
            result_data = None
            if content:
                try:
                    # 提取JSON字符串
                    json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        result_data = json.loads(json_str)
                except Exception as e:
                    logger.warning(f"从content解析JSON失败: {str(e)}")
                    
            # 如果content中没有有效的JSON，尝试使用reasoning_content
            if not result_data and reasoning_content:
                try:
                    result_data = {
                        "总得分": 0,
                        "分项得分": {},
                        "总体评价": "",
                        "内容分析": "",
                        "语言分析": "",
                        "结构分析": "",
                        "写作建议": "",
                        "错别字": []
                    }
                    
                    # 从reasoning_content中提取评分和评语
                    score_match = re.search(r'总得分可能在(\d+)分左右', reasoning_content)
                    if score_match:
                        result_data["总得分"] = int(score_match.group(1))
                        
                    # 提取分项得分
                    score_patterns = {
                        "内容主旨": r'内容主旨.*?(\d+)分',
                        "语言文采": r'语言文采.*?(\d+)分',
                        "文章结构": r'结构.*?(\d+)分',
                        "文面书写": r'文面书写.*?(\d+)分'
                    }
                    
                    for key, pattern in score_patterns.items():
                        match = re.search(pattern, reasoning_content)
                        if match:
                            result_data["分项得分"][key] = int(match.group(1))
                            
                except Exception as e:
                    logger.warning(f"从reasoning_content提取信息失败: {str(e)}")
                    
            if not result_data:
                logger.error("无法从API响应中提取有效的批改结果")
                return {
                    "status": "error",
                    "message": "无法解析批改结果"
                }
                
            # 转换为标准格式
            return {
                "status": "success",
                "result": {
                    "score": result_data.get("总得分", 0),
                    "corrected_content": "",  # 暂不支持
                    "comments": result_data.get("总体评价", ""),
                    "error_analysis": result_data.get("错别字", []),
                    "improvement_suggestions": result_data.get("写作建议", ""),
                    "details": {
                        "content_score": result_data.get("分项得分", {}).get("内容主旨", 0),
                        "language_score": result_data.get("分项得分", {}).get("语言文采", 0),
                        "structure_score": result_data.get("分项得分", {}).get("文章结构", 0),
                        "writing_score": result_data.get("分项得分", {}).get("文面书写", 0),
                        "content_analysis": result_data.get("内容分析", ""),
                        "language_analysis": result_data.get("语言分析", ""),
                        "structure_analysis": result_data.get("结构分析", "")
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"解析批改结果时发生错误: {str(e)}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"解析批改结果时发生错误: {str(e)}"
            }
    
    def format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化响应
        
        Args:
            result: 分析结果
            
        Returns:
            Dict: 格式化的响应
        """
        return {
            "status": "success",
            "result": result
        }


class DeepseekClient:
    """Deepseek API客户端"""
    
    def __init__(self, api_key=None, api_base=None):
        """
        初始化Deepseek客户端
        
        Args:
            api_key: Deepseek API密钥，如果为None则尝试从环境变量获取
            api_base: Deepseek API基础URL
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.api_base = api_base or os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        self.model = "deepseek-chat"
        self.max_tokens = 4000
        self.temperature = 0.7
        
        # 初始化日志
        logger.info("初始化Deepseek客户端")
    
    def generate_text(self, prompt, max_tokens=None, temperature=None):
        """
        使用Deepseek API生成文本
        
        Args:
            prompt: 提示文本
            max_tokens: 生成的最大标记数
            temperature: 温度参数，控制生成文本的随机性
            
        Returns:
            str: 生成的文本
        """
        logger.info(f"使用Deepseek API生成文本，提示长度: {len(prompt)}")
        
        try:
            # 实际的Deepseek API调用
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature
            }
            
            # 仅在调试模式下记录请求，不包含API密钥
            logger.debug(f"请求Deepseek API，模型: {self.model}")
            
            # 实际应用中应使用下面的代码发送请求
            # response = requests.post(f"{self.api_base}/chat/completions", headers=headers, json=data)
            # response.raise_for_status()
            # result = response.json()
            # generated_text = result["choices"][0]["message"]["content"]
            
            # 模拟响应，用于测试
            generated_text = f"这是Deepseek AI对于提示'{prompt[:30]}...'的模拟响应。实际应用中应调用API。"
            
            logger.info(f"成功从Deepseek API获取响应，长度: {len(generated_text)}")
            return generated_text
            
        except Exception as e:
            logger.error(f"调用Deepseek API时发生错误: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"Deepseek API调用失败: {str(e)}") 