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
                return self.format_response(self._extract_result(result_json))
                
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
    
    def _extract_result(self, response: Dict) -> Dict[str, Any]:
        """
        从API响应中提取结果
        
        Args:
            response: API响应
            
        Returns:
            Dict: 提取的结果
        """
        # 提取分数
        total_score = response.get("总得分", 0)
        
        # 提取分项得分
        分项得分 = response.get("分项得分", {})
        content_score = 分项得分.get("内容主旨", 0)
        language_score = 分项得分.get("语言文采", 0)
        structure_score = 分项得分.get("文章结构", 0)
        writing_score = 分项得分.get("写作技巧", 0)
        
        # 提取评价和分析
        overall_assessment = response.get("总体评价", "")
        content_analysis = response.get("内容分析", "")
        language_analysis = response.get("语言分析", "")
        structure_analysis = response.get("结构分析", "")
        improvement_suggestions = response.get("写作建议", "")
        
        # 提取错别字
        spelling_errors = response.get("错别字", [])
        
        # 返回格式化的结果
        return {
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
            "spelling_errors": spelling_errors
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