#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI批改服务模块
负责与AI服务交互，发送作文内容和接收批改结果
"""

import os
import json
import requests
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime

from app.utils.exceptions import AIServiceError, ValidationError
from app.config import config

# 配置日志记录器
logger = logging.getLogger('app.core.correction.ai')

class AIService:
    """
    AI批改服务类
    
    负责与AI API交互，处理作文批改请求和结果解析
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AIService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化AI批改服务"""
        if self._initialized:
            return
            
        # 从配置中加载API密钥和设置
        self.api_key = config.AI_CONFIG.get('API_KEY', '')
        self.base_url = config.AI_CONFIG.get('BASE_URL', '')
        self.model = config.AI_CONFIG.get('MODEL', 'deepseek-chat')
        self.temperature = config.AI_CONFIG.get('TEMPERATURE', 0.1)
        self.max_tokens = config.AI_CONFIG.get('MAX_TOKENS', 4000)
        self.timeout = config.AI_CONFIG.get('TIMEOUT', 60)
        
        # 验证必要配置
        if not self.api_key:
            logger.warning("AI服务API密钥未配置，请设置环境变量或配置文件")
            
        self._initialized = True
    
    def correct_essay(self, content: str, grade: str, title: str = None) -> Dict[str, Any]:
        """
        调用AI接口批改作文
        
        Args:
            content: 作文内容
            grade: 年级水平
            title: 作文标题
            
        Returns:
            Dict: 批改结果
            
        Raises:
            AIServiceError: 如果AI服务调用失败
        """
        if not self.api_key:
            raise AIServiceError("AI服务API密钥未配置")
            
        # 准备提示词
        prompt = self._prepare_correction_prompt(content, grade, title)
        
        try:
            # 调用AI API
            response = self._call_ai_api(prompt)
            
            # 解析响应
            ai_result = self._parse_ai_response(response)
            
            # 格式化结果
            return self._format_correction_result(ai_result)
            
        except requests.RequestException as e:
            logger.error(f"AI API请求异常: {str(e)}", exc_info=True)
            raise AIServiceError(f"AI服务连接失败: {str(e)}")
            
        except json.JSONDecodeError as e:
            logger.error(f"AI响应解析异常: {str(e)}", exc_info=True)
            raise AIServiceError(f"AI响应格式错误: {str(e)}")
            
        except Exception as e:
            logger.error(f"AI批改未知异常: {str(e)}", exc_info=True)
            raise AIServiceError(f"AI批改错误: {str(e)}")
    
    def _call_ai_api(self, prompt: str) -> Dict[str, Any]:
        """
        调用AI API
        
        Args:
            prompt: 提示词
            
        Returns:
            Dict: API响应
            
        Raises:
            requests.RequestException: 如果API调用失败
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一位专业的中文作文批改老师，擅长评价学生作文并给出详细反馈。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            response = requests.post(
                self.base_url, 
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"API调用失败: {str(e)}", exc_info=True)
            raise
    
    def _parse_ai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析AI响应
        
        Args:
            response: API响应
            
        Returns:
            Dict: 提取的批改结果
            
        Raises:
            json.JSONDecodeError: 如果解析失败
        """
        try:
            # 提取消息内容
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                raise ValueError("API响应中没有找到content字段")
            
            # 提取JSON代码块
            json_start = content.find('```json')
            json_end = content.find('```', json_start + 7)
            
            if json_start == -1 or json_end == -1:
                raise ValueError("未找到JSON代码块")
            
            # 提取并解析JSON
            json_text = content[json_start + 7:json_end].strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {str(e)}")
                logger.debug(f"JSON文本: {json_text}")
                raise
                
        except Exception as e:
            logger.error(f"解析AI响应失败: {str(e)}")
            logger.debug(f"原始响应: {json.dumps(response, ensure_ascii=False)}")
            if isinstance(e, json.JSONDecodeError):
                raise
            raise json.JSONDecodeError(f"解析AI响应时发生错误: {str(e)}", doc="", pos=0)
    
    def _prepare_correction_prompt(self, content: str, grade: str, title: str = None) -> str:
        """
        准备AI批改提示词，使用评分规则
        
        Args:
            content: 作文内容
            grade: 年级水平
            title: 作文标题
            
        Returns:
            str: 完整的提示词
        """
        grade_levels = {
            'primary': '小学',
            'junior': '初中',
            'senior': '高中',
            'college': '大学'
        }
        
        chinese_grade = grade_levels.get(grade, '未知')
        text_length = len(content)
        
        # 基于原有评分规则构建提示词
        prompt = f"""<请你作为广东{chinese_grade}语文阅卷老师，按照以下标准对作文进行全面评分和详细分析：

作文标题：{title if title else "无标题"}
作文内容：{content[:3000]}{"..." if len(content) > 3000 else ""}
字数：{text_length}字

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

必须以JSON格式返回结果，结构如下：
{self.get_json_template()}
"""
        
        return prompt
    
    def get_json_template(self) -> str:
        """
        返回评分结果的JSON模板
        
        Returns:
            str: JSON模板字符串
        """
        return """
```json
{
    "总得分": 45,
    "等级评定": "A-优秀",
    "分项得分": {
        "内容主旨": 18,
        "语言文采": 14,
        "文章结构": 9,
        "文面书写": 4
    },
    "错别字": [
        "错别字1->正确写法1",
        "错别字2->正确写法2"
    ],
    "总体评价": "这篇作文...(详细评价)",
    "内容分析": "文章主题...(详细分析)",
    "语言分析": "本文语言流畅，使用了多种修辞手法，词汇丰富...(详细分析)",
    "结构分析": "文章结构...(详细分析)",
    "写作建议": "建议作者...(具体建议)"
}
```
"""
    
    def _format_correction_result(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化AI批改结果为统一格式
        
        Args:
            ai_result: AI返回的原始结果
            
        Returns:
            Dict: 格式化后的结果，确保与数据库字段类型匹配
        """
        try:
            # 提取分数（确保是浮点数）
            total_score = float(ai_result.get('总得分', 0))
            
            # 提取分项得分（确保是浮点数）
            分项得分 = ai_result.get('分项得分', {})
            content_score = float(分项得分.get('内容主旨', 0))
            language_score = float(分项得分.get('语言文采', 0))
            structure_score = float(分项得分.get('文章结构', 0))
            writing_score = float(分项得分.get('文面书写', 0))
            
            # 提取等级（保留完整的等级评定）
            full_level = ai_result.get('等级评定', 'C-合格')
            # 提取等级字母部分用于数据库存储
            level = full_level.split('-')[0] if '-' in full_level else full_level
            
            # 提取错别字（已经是简化格式）
            spelling_errors = ai_result.get('错别字', [])
            
            # 构建错误分析（作为JSON对象存储）
            error_analysis = {
                "spelling_errors": spelling_errors,
                "content_issues": {
                    "等级评定": full_level,
                    "内容分析": ai_result.get('内容分析', ''),
                    "语言分析": ai_result.get('语言分析', ''),
                    "结构分析": ai_result.get('结构分析', '')
                }
            }
            
            # 构建评语（作为Text存储）
            comments = ai_result.get('总体评价', '')
            
            # 构建改进建议（作为Text存储）
            improvement_suggestions = ai_result.get('写作建议', '')
            
            # 返回统一格式的结果
            return {
                "score": total_score,  # Float
                "level": level,  # String
                "content_score": content_score,  # Float
                "language_score": language_score,  # Float
                "structure_score": structure_score,  # Float
                "writing_score": writing_score,  # Float
                "error_analysis": error_analysis,  # JSON
                "comments": comments,  # Text
                "improvement_suggestions": improvement_suggestions,  # Text
                "corrected_content": None  # 当前API不提供修改后的内容
            }
            
        except Exception as e:
            logger.error(f"格式化批改结果失败: {str(e)}", exc_info=True)
            logger.debug(f"原始结果: {json.dumps(ai_result, ensure_ascii=False)}")
            # 返回基本结果
            return {
                "score": 0.0,  # Float
                "level": "C",  # String
                "content_score": 0.0,  # Float
                "language_score": 0.0,  # Float
                "structure_score": 0.0,  # Float
                "writing_score": 0.0,  # Float
                "error_analysis": {  # JSON
                    "等级评定": "C-合格",
                    "spelling_errors": [],
                    "content_issues": {
                        "总体评价": "评分失败，请重试"
                    }
                },
                "comments": "评分失败，请重试",  # Text
                "improvement_suggestions": "",  # Text
                "corrected_content": None  # Text
            }
    
    def _safe_extract_score(self, score_value: Any) -> str:
        """
        安全地提取并标准化分数值
        
        Args:
            score_value: 原始分数值（可能是字符串或数字）
            
        Returns:
            str: 标准化的分数字符串
        """
        if isinstance(score_value, str):
            # 去除所有非数字字符
            digits = ''.join(filter(str.isdigit, score_value))
            return digits if digits else '0'
        elif isinstance(score_value, (int, float)):
            return str(int(score_value))
        else:
            return '0'
