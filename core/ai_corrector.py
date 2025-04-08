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
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from utils.exceptions import AIServiceError, ValidationError
from config.app_config import AI_CONFIG, APP_CONFIG

# 配置日志记录器
logger = logging.getLogger('autocorrection.ai')

class AICorrectionService:
    """
    AI批改服务类
    
    负责与AI API交互，处理作文批改请求和结果解析
    """
    
    def __init__(self):
        """初始化AI批改服务"""
        # 从配置中加载API密钥和设置
        self.api_key = AI_CONFIG.get('API_KEY', '')
        self.base_url = AI_CONFIG.get('BASE_URL', '')
        self.model = AI_CONFIG.get('MODEL', 'deepseek-chat')
        self.temperature = AI_CONFIG.get('TEMPERATURE', 0.1)
        self.max_tokens = AI_CONFIG.get('MAX_TOKENS', 4000)
        self.timeout = AI_CONFIG.get('TIMEOUT', 60)
        
        # 验证必要配置
        if not self.api_key:
            logger.warning("AI服务API密钥未配置，请设置环境变量或配置文件")
    
    def process_async(self, essay_id: int, content: str, grade: str, title: str,
                    completion_callback: Optional[Callable] = None) -> None:
        """
        异步处理作文批改
        
        Args:
            essay_id: 作文ID
            content: 作文内容
            grade: 年级水平
            title: 作文标题
            completion_callback: 完成时的回调函数
        """
        # 创建异步处理线程
        correction_thread = threading.Thread(
            target=self._process_correction_task,
            args=(essay_id, content, grade, title, completion_callback)
        )
        correction_thread.daemon = True
        correction_thread.start()
        
        logger.info(f"已启动异步批改任务，作文ID: {essay_id}")
    
    def _process_correction_task(self, essay_id: int, content: str, grade: str, 
                               title: str, completion_callback: Optional[Callable] = None) -> None:
        """
        作文批改任务处理函数
        
        Args:
            essay_id: 作文ID
            content: 作文内容
            grade: 年级水平
            title: 作文标题
            completion_callback: 完成时的回调函数
        """
        try:
            # 调用AI批改
            result = self.correct_essay(content, grade, title)
            
            # 调用回调函数
            if completion_callback:
                completion_callback(essay_id, result)
                
            logger.info(f"作文批改完成，ID: {essay_id}")
            
        except Exception as e:
            logger.error(f"作文批改异常，ID: {essay_id}: {str(e)}", exc_info=True)
            
            # 调用回调函数报告错误
            if completion_callback:
                completion_callback(essay_id, error=str(e))
    
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
    
    def _prepare_correction_prompt(self, content: str, grade: str, title: str = None) -> str:
        """
        准备AI批改提示词，使用原有评分规则
        
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
"总得分": "45",
"等级评定": "A-优秀",
"分项得分": {
    "内容主旨": "18",
    "语言文采": "14",
    "文章结构": "9",
    "文面书写": "4"
},
"扣分项": {
    "错别字": [
    {"错误": "错别字1", "位置": "第二段第3行", "正确写法": "正确写法1", "上下文": "包含错别字的上下文"},
    {"错误": "错别字2", "位置": "第三段第1行", "正确写法": "正确写法2", "上下文": "包含错别字的上下文"}
    ],
    "其他扣分": ["无标题扣2分"]
},
"总体评价": "这篇作文...(详细评价)",
"内容分析": "文章主题...(详细分析)",
"语言分析": "本文语言流畅，使用了多种修辞手法，词汇丰富...(详细分析)",
"结构分析": "文章结构...(详细分析)",
"写作建议": "建议作者...(具体建议)"
}
```
"""
    
    def _call_ai_api(self, prompt: str) -> Dict[str, Any]:
        """
        调用AI API
        
        Args:
            prompt: 提示词
            
        Returns:
            Dict: API响应
            
        Raises:
            AIServiceError: 如果API调用失败
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            logger.info(f"发送API请求，模型: {self.model}, 提示词长度: {len(prompt)}")
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            # 检查HTTP状态码
            response.raise_for_status()
            
            # 解析JSON响应
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"API请求失败: {str(e)}", exc_info=True)
            raise AIServiceError(f"AI服务请求失败: {str(e)}")
    
    def _parse_ai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析AI API响应
        
        Args:
            response: API响应
            
        Returns:
            Dict: 解析后的批改结果
            
        Raises:
            AIServiceError: 如果响应解析失败
        """
        try:
            # 提取返回的内容
            content = response['choices'][0]['message']['content']
            
            # 尝试从内容中提取JSON
            json_start = content.find('{')
            json_end = content.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                # 提取JSON字符串
                json_str = content[json_start:json_end+1]
                
                try:
                    # 解析JSON
                    correction_data = json.loads(json_str)
                    
                    # 验证所需字段
                    required_fields = ['总得分', '等级评定', '分项得分']
                    for field in required_fields:
                        if field not in correction_data:
                            logger.warning(f"AI响应缺少必要字段: {field}")
                    
                    return correction_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {str(e)}, 内容: {json_str[:100]}...")
                    raise AIServiceError(f"AI响应格式错误: {str(e)}")
            
            # 如果找不到有效的JSON，尝试作为纯文本处理
            logger.warning("未找到有效的JSON格式响应，尝试解析纯文本")
            
            try:
                # 简单提取分数
                score_line = [line for line in content.split('\n') if '总得分' in line or '总分' in line]
                score = int(''.join(filter(str.isdigit, score_line[0]))) if score_line else 0
                
                return {
                    '总得分': str(score),
                    '等级评定': 'C',
                    '分项得分': {
                        '内容主旨': '10',
                        '语言文采': '7',
                        '文章结构': '5',
                        '文面书写': '3'
                    },
                    '总体评价': content
                }
            except Exception:
                raise AIServiceError("无法解析AI响应")
                
        except (KeyError, IndexError) as e:
            logger.error(f"提取AI响应内容失败: {str(e)}", exc_info=True)
            raise AIServiceError(f"无法从AI响应中提取内容: {str(e)}")
    
    def _format_correction_result(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化AI批改结果为统一格式
        
        Args:
            ai_result: AI返回的原始结果
            
        Returns:
            Dict: 格式化后的结果
        """
        try:
            # 提取分数
            total_score = self._safe_extract_score(ai_result.get('总得分', '0'))
            
            # 提取分项得分
            分项得分 = ai_result.get('分项得分', {})
            content_score = self._safe_extract_score(分项得分.get('内容主旨', '0'))
            language_score = self._safe_extract_score(分项得分.get('语言文采', '0'))
            structure_score = self._safe_extract_score(分项得分.get('文章结构', '0'))
            writing_score = self._safe_extract_score(分项得分.get('文面书写', '0'))
            
            # 提取等级
            level = ai_result.get('等级评定', 'C')
            if '-' in level:
                level = level.split('-')[0]
                
            # 提取错别字
            spelling_errors = []
            if '扣分项' in ai_result and isinstance(ai_result['扣分项'], dict) and '错别字' in ai_result['扣分项']:
                spelling_errors = ai_result['扣分项']['错别字']
            
            # 构建反馈内容
            feedback = {
                "总体评价": ai_result.get('总体评价', ''),
                "内容分析": ai_result.get('内容分析', ''),
                "语言分析": ai_result.get('语言分析', ''),
                "结构分析": ai_result.get('结构分析', ''),
                "写作建议": ai_result.get('写作建议', ''),
                "错别字": spelling_errors
            }
            
            # 返回统一格式的结果
            return {
                "score": int(total_score),
                "level": level,
                "content_score": int(content_score),
                "language_score": int(language_score),
                "structure_score": int(structure_score),
                "writing_score": int(writing_score),
                "feedback": json.dumps(feedback, ensure_ascii=False)
            }
            
        except Exception as e:
            logger.error(f"格式化批改结果失败: {str(e)}", exc_info=True)
            # 返回基本结果
            return {
                "score": 0,
                "level": "C",
                "content_score": 0,
                "language_score": 0,
                "structure_score": 0,
                "writing_score": 0,
                "feedback": json.dumps({"总体评价": "评分失败，请重试"}, ensure_ascii=False)
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

# 创建单例实例
ai_service = AICorrectionService() 