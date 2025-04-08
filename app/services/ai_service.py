#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI服务模块
提供文本生成和图像识别功能
"""

import os
import json
import base64
import time
import logging
import requests
from typing import Dict, Any, Optional, List, Union
import traceback

from app.config import config

logger = logging.getLogger(__name__)

class AIService:
    """AI服务类，提供文本生成和图像识别功能"""
    
    def __init__(self):
        """初始化AI服务"""
        # 文本生成服务配置
        self.text_api_url = config.AI_CONFIG.get('text_api_url', '')
        self.text_api_key = config.AI_CONFIG.get('text_api_key', '')
        self.model_name = config.AI_CONFIG.get('model_name', 'qwen-max')
        self.max_tokens = config.AI_CONFIG.get('max_tokens', 2048)
        self.temperature = config.AI_CONFIG.get('temperature', 0.7)
        
        # 图像识别服务配置
        self.image_api_url = config.AI_CONFIG.get('image_api_url', '')
        self.image_api_key = config.AI_CONFIG.get('image_api_key', '')
        self.image_model_name = config.AI_CONFIG.get('image_model_name', 'qwen-vl-plus')
        
        # 请求超时设置
        self.timeout = config.AI_CONFIG.get('timeout', 30)
        
        # 重试设置
        self.max_retries = config.AI_CONFIG.get('max_retries', 3)
        self.retry_delay = config.AI_CONFIG.get('retry_delay', 1)
    
    def generate_text(self, prompt: str, system_prompt: str = None, 
                     temperature: float = None, max_tokens: int = None) -> Dict[str, Any]:
        """
        生成文本内容
        
        Args:
            prompt: 提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成token数
        
        Returns:
            Dict: 生成结果
        """
        if not prompt:
            return {'status': 'error', 'message': '提示词不能为空'}
        
        if not self.text_api_url or not self.text_api_key:
            logger.error("文本生成服务配置不完整")
            return {'status': 'error', 'message': 'AI服务配置不完整'}
        
        # 使用传入参数或默认参数
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        # 构建请求
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.text_api_key}'
        }
        
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加用户提示词
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 发送请求并重试
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.text_api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 处理返回结果
                    if 'choices' in result and len(result['choices']) > 0:
                        generated_text = result['choices'][0].get('message', {}).get('content', '')
                        
                        return {
                            'status': 'success',
                            'text': generated_text,
                            'model': self.model_name,
                            'usage': result.get('usage', {})
                        }
                    else:
                        logger.warning(f"AI服务返回了异常结果: {result}")
                        return {'status': 'error', 'message': '生成结果异常', 'raw_response': result}
                else:
                    logger.warning(f"AI服务返回了非200状态码: {response.status_code}, 响应: {response.text}")
                    
                    # 判断是否需要重试
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        return {
                            'status': 'error',
                            'message': f'AI服务响应错误: {response.status_code}',
                            'raw_response': response.text
                        }
            
            except Exception as e:
                logger.error(f"调用AI文本生成服务时发生错误: {str(e)}", exc_info=True)
                
                # 判断是否需要重试
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return {'status': 'error', 'message': f'调用AI服务时发生错误: {str(e)}'}
        
        return {'status': 'error', 'message': '超过最大重试次数'}
    
    def recognize_text_from_image(self, image_data: Union[str, bytes]) -> Dict[str, Any]:
        """
        从图片中识别文本
        
        Args:
            image_data: 图片数据，可以是文件路径或图片字节数据
        
        Returns:
            Dict: 识别结果
        """
        if not image_data:
            return {'status': 'error', 'message': '图片数据不能为空'}
        
        if not self.image_api_url or not self.image_api_key:
            logger.error("图像识别服务配置不完整")
            return {'status': 'error', 'message': 'AI图像识别服务配置不完整'}
        
        try:
            # 处理图片数据
            if isinstance(image_data, str) and os.path.exists(image_data):
                # 从路径读取图片
                with open(image_data, 'rb') as f:
                    image_bytes = f.read()
                    base64_image = base64.b64encode(image_bytes).decode('utf-8')
            elif isinstance(image_data, bytes):
                # 直接使用图片字节数据
                base64_image = base64.b64encode(image_data).decode('utf-8')
            else:
                return {'status': 'error', 'message': '无效的图片数据格式'}
            
            # 构建请求
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.image_api_key}'
            }
            
            # 构建文本提取提示词
            prompt = "请提取图片中的所有文字内容，保持段落格式，只返回提取的文字，不需要任何解释"
            
            payload = {
                "model": self.image_model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "image": f"data:image/jpeg;base64,{base64_image}"}
                        ]
                    }
                ],
                "temperature": 0.1,  # 低温度，使输出更确定性
                "max_tokens": 4096
            }
            
            # 发送请求并重试
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        self.image_api_url,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # 处理返回结果
                        if 'choices' in result and len(result['choices']) > 0:
                            extracted_text = result['choices'][0].get('message', {}).get('content', '')
                            
                            return {
                                'status': 'success',
                                'text': extracted_text,
                                'model': self.image_model_name,
                                'usage': result.get('usage', {})
                            }
                        else:
                            logger.warning(f"图像识别服务返回了异常结果: {result}")
                            return {'status': 'error', 'message': '识别结果异常', 'raw_response': result}
                    else:
                        logger.warning(f"图像识别服务返回了非200状态码: {response.status_code}, 响应: {response.text}")
                        
                        # 判断是否需要重试
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay * (attempt + 1))
                            continue
                        else:
                            return {
                                'status': 'error',
                                'message': f'图像识别服务响应错误: {response.status_code}',
                                'raw_response': response.text
                            }
                
                except Exception as e:
                    logger.error(f"调用图像识别服务时发生错误: {str(e)}", exc_info=True)
                    
                    # 判断是否需要重试
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        return {'status': 'error', 'message': f'调用图像识别服务时发生错误: {str(e)}'}
            
            return {'status': 'error', 'message': '超过最大重试次数'}
        
        except Exception as e:
            logger.error(f"处理图片识别时发生错误: {str(e)}")
            traceback.print_exc()
            return {'status': 'error', 'message': f'处理图片识别时发生错误: {str(e)}'}
    
    def unified_essay_scoring(self, essay_text: str, grading_criteria: str = None) -> Dict[str, Any]:
        """使用AI模型对作文进行统一评分和生成评语 (Placeholder)"""
        logger.info(f"统一评分请求，作文长度: {len(essay_text)}")
        
        # TODO: Implement actual scoring logic using self.generate_text or a specific endpoint
        # Example prompt structure:
        # system_prompt = "你是一个严格的作文评分助手..."
        # prompt = f"请根据以下评分标准对作文进行评分，并给出详细评语:\n评分标准:{grading_criteria}\n作文内容:\n{essay_text}"
        
        # Simulate AI response for now
        simulated_score = 85
        simulated_feedback = "文章结构清晰，论点明确，但部分论据不够充分。语言表达流畅，偶有语法错误。"
        
        return {
            'status': 'success',
            'score': simulated_score,
            'feedback': simulated_feedback,
            'model': self.model_name # Indicate which model was used (or simulated)
        }

    def correct_essay(self, essay_text: str) -> Dict[str, Any]:
        """使用AI模型对作文进行批改 (Placeholder)"""
        if not essay_text:
            return {'status': 'error', 'message': '作文内容不能为空'}
        
        # 构建批改系统提示词
        system_prompt = """你是一个专业的中文写作老师，擅长批改中文作文。请根据以下标准对提供的作文进行评价和修改：

1. 内容评价（20分）：评估作文的主题是否明确，内容是否充实，是否有深度和广度。
2. 结构布局（20分）：评估作文结构是否完整，段落划分是否合理，过渡是否自然。
3. 语言表达（30分）：评估语言是否流畅，用词是否准确，句式是否多样。
4. 文体特点（15分）：评估是否符合特定文体的要求，风格是否鲜明。
5. 语法错误（15分）：评估标点、拼写、语法使用是否规范。

请按以下格式输出批改结果：

【总体评分】：总分和简短总评
【内容评价】：分数和详细评语
【结构布局】：分数和详细评语
【语言表达】：分数和详细评语
【文体特点】：分数和详细评语
【语法错误】：分数和详细评语
【修改建议】：具体、有针对性的修改建议和指导

请保持专业、客观、鼓励性的批改风格，既指出问题，也肯定优点。"""
        
        # 调用文本生成接口进行批改
        return self.generate_text(
            prompt=essay_text,
            system_prompt=system_prompt,
            temperature=0.3,  # 低温度，使批改结果更确定性
            max_tokens=3072   # 批改需要较长的输出
        )
    
    def health_check(self) -> Dict[str, Any]:
        """
        检查AI服务是否正常运行
        
        Returns:
            Dict: 服务健康状态
        """
        results = {}
        
        # 检查文本生成服务
        if self.text_api_url and self.text_api_key:
            try:
                test_response = self.generate_text(
                    prompt="你好",
                    max_tokens=10
                )
                text_status = test_response.get('status') == 'success'
                results['text_service'] = {
                    'status': 'available' if text_status else 'unavailable',
                    'message': '服务正常' if text_status else test_response.get('message', '未知错误')
                }
            except Exception as e:
                results['text_service'] = {
                    'status': 'unavailable',
                    'message': f'服务异常: {str(e)}'
                }
        else:
            results['text_service'] = {
                'status': 'unconfigured',
                'message': '服务未配置'
            }
        
        # 检查图像识别服务
        if self.image_api_url and self.image_api_key:
            # 这里可以选择不实际测试图像服务，因为可能消耗额度
            results['image_service'] = {
                'status': 'configured',
                'message': '服务已配置，但未实际测试'
            }
        else:
            results['image_service'] = {
                'status': 'unconfigured',
                'message': '服务未配置'
            }
        
        # 检查整体状态
        if all(service['status'] in ['available', 'configured'] for service in results.values()):
            overall_status = 'healthy'
        elif any(service['status'] == 'available' for service in results.values()):
            overall_status = 'partially_available'
        elif any(service['status'] == 'configured' for service in results.values()):
            overall_status = 'configured'
        else:
            overall_status = 'unavailable'
        
        return {
            'status': overall_status,
            'services': results
        } 