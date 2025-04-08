#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
阿里云通义千问客户端
用于与阿里云通义千问API交互
"""

import os
import json
import logging
import traceback
from typing import Dict, Any, List, Optional, Union
import requests

from app.core.ai.api_client import BaseAPIClient, APIError
from config.ai_config import AI_CONFIG

# 配置日志
logger = logging.getLogger(__name__)

class AliyunQianwenClient(BaseAPIClient):
    """阿里云通义千问客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, verify_ssl: bool = True):
        """
        初始化通义千问客户端
        
        Args:
            api_key: 阿里云API密钥
            base_url: 阿里云API基础URL
            model: 使用的模型
            verify_ssl: 是否验证SSL证书
        """
        self.model = model or "qwen-max"
        super().__init__(api_key, base_url, verify_ssl)
        
        logger.info(f"通义千问客户端初始化完成，使用模型: {self.model}")
    
    @property
    def provider_name(self) -> str:
        """提供商名称"""
        return "aliyun_qianwen"
    
    def _load_config_from_env(self):
        """从环境变量加载配置"""
        # 从环境变量加载API密钥
        if not self.api_key:
            self.api_key = os.environ.get("ALIYUN_API_KEY", "")
        
        # 从环境变量加载基础URL
        if not self.base_url:
            self.base_url = os.environ.get("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/api/v1")
        
        # 从环境变量加载模型
        if not self.model:
            self.model = os.environ.get("ALIYUN_MODEL", "qwen-max")
    
    def analyze_essay(self, content: str) -> Dict[str, Any]:
        """
        使用通义千问分析作文
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 分析结果
        """
        try:
            logger.info(f"使用通义千问分析作文，内容长度: {len(content)}")
            
            system_prompt = """
            你是一位专业的中文作文评价老师。你的任务是批改学生的作文。
            你需要指出作文中的错误并给出修改建议。
            同时评价作文的内容、语言、结构和书写，并提供改进建议和评分。
            """
            
            user_prompt = f"""
            请对下面的作文进行全面评价和批改，包括：
            1. 总分（满分100分）
            2. 分项得分（内容、语言、结构、书写，每项满分100分）
            3. 总体评价（200字左右）
            4. 错误指正和修改建议
            5. 内容、语言、结构方面的具体分析
            6. 改进建议
            
            作文内容：
            {content}
            
            请使用以下JSON格式返回结果：
            {{
                "总得分": 85,
                "分项得分": {{
                    "内容主旨": 80,
                    "语言文采": 85,
                    "文章结构": 90,
                    "写作技巧": 85
                }},
                "总体评价": "这是一篇...",
                "内容分析": "文章主题明确...",
                "语言分析": "语言表达流畅...",
                "结构分析": "文章结构合理...",
                "写作建议": "建议在...",
                "错别字": ["错误1->正确1", "错误2->正确2"]
            }}
            
            请只返回JSON格式的结果，不要包含其他说明文字。
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 构建请求体，阿里云API格式
            data = {
                "model": self.model,
                "input": {
                    "messages": messages
                },
                "parameters": {
                    "temperature": 0.5,
                    "top_p": 0.8,
                    "result_format": "message"
                }
            }
            
            try:
                # 注意: 阿里云API的端点和参数可能与OpenAI有所不同
                # 这里假设调用的是dashscope API
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"{self.base_url}/services/aigc/text-generation/generation",
                    headers=headers,
                    json=data,
                    timeout=60
                )
                
                if response.status_code != 200:
                    logger.error(f"通义千问API请求失败: {response.status_code}, {response.text}")
                    return {
                        "status": "error",
                        "message": f"API请求失败: {response.status_code}, {response.text}"
                    }
                
                result = response.json()
                
                # 从返回结果中提取内容
                if "output" in result and "text" in result["output"]:
                    content = result["output"]["text"]
                    try:
                        # 尝试解析JSON
                        json_content = json.loads(content)
                        return self._extract_result(json_content)
                    except json.JSONDecodeError:
                        # 尝试从文本中提取JSON部分
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            json_str = content[json_start:json_end]
                            try:
                                json_content = json.loads(json_str)
                                return self._extract_result(json_content)
                            except json.JSONDecodeError:
                                logger.error(f"无法从文本中提取有效JSON")
                        
                        return {
                            "status": "error",
                            "message": "无法解析返回的JSON内容"
                        }
                else:
                    logger.error(f"通义千问响应格式异常: {result}")
                    return {
                        "status": "error",
                        "message": "API响应格式错误"
                    }
                
            except Exception as e:
                logger.error(f"通义千问API请求异常: {str(e)}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"API请求异常: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"使用通义千问分析作文失败: {str(e)}", exc_info=True)
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
        try:
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
            
            return {
                "status": "success",
                "result": {
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
                    "spelling_errors": {
                        "错别字": spelling_errors
                    }
                }
            }
        except Exception as e:
            logger.error(f"解析通义千问响应失败: {str(e)}")
            return {
                "status": "error",
                "message": f"解析响应失败: {str(e)}"
            }
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        从图片中提取文本
        
        Args:
            image_path: 图片路径
            
        Returns:
            str: 提取的文本
        """
        try:
            logger.info(f"从图片提取文本: {image_path}")
            
            # 读取图片并编码为base64
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
                
            return self._process_image(image_bytes)
            
        except Exception as e:
            logger.error(f"从图片提取文本时出错: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"图片文本提取失败: {str(e)}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        从PDF中提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            str: 提取的文本
        """
        try:
            logger.info(f"从PDF提取文本: {pdf_path}")
            
            user_prompt = "这是一个PDF文档，请提取其中的所有文本内容，保持原始格式。只需要返回提取的文本，不需要任何额外的解释或者分析。"
            
            # 读取PDF并编码为base64
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            
            # 构建请求数据
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "document", "document": {"format": "pdf", "content": pdf_base64}}
                        ]
                    }
                ],
                "parameters": {
                    "result_format": "text",
                    "temperature": 0.1
                }
            }
            
            # 发送请求
            response = self._api_request("POST", "chat/completions", data=data)
            
            # 提取文本
            if "choices" in response and len(response["choices"]) > 0:
                extracted_text = response["choices"][0]["message"]["content"]
                logger.info(f"成功从PDF提取文本，长度: {len(extracted_text)}")
                return extracted_text
            else:
                logger.error("未能从PDF中提取文本")
                raise Exception("未能从PDF中提取文本")
                
        except Exception as e:
            logger.error(f"从PDF提取文本时出错: {str(e)}\n{traceback.format_exc()}")
            raise Exception(f"PDF文本提取失败: {str(e)}")
    
    def _process_image(self, image_bytes: bytes) -> str:
        """
        处理图片内容
        
        Args:
            image_bytes: 图片字节
            
        Returns:
            str: 提取的文本
        """
        # 将图片编码为base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # 构建请求数据
        user_prompt = "请提取图片中的所有文字内容，保持原始格式。"
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image", "image": image_base64}
                    ]
                }
            ],
            "parameters": {
                "result_format": "text",
                "temperature": 0.1
            }
        }
        
        # 发送请求
        response = self._api_request("POST", "chat/completions", data=data)
        
        # 提取文本
        if "choices" in response and len(response["choices"]) > 0:
            extracted_text = response["choices"][0]["message"]["content"]
            logger.info(f"成功从图片提取文本，长度: {len(extracted_text)}")
            return extracted_text
        else:
            logger.error("未能从图片中提取文本")
            raise Exception("未能从图片中提取文本") 