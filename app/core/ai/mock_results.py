#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提供创建模拟批改结果的功能
用于测试和开发环境，生成模拟的AI批改数据
"""

import json
import random
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

def create_mock_result(
    content: str,
    score: Optional[int] = None,
    error_count: Optional[int] = None,
    model: str = "mock-model"
) -> Dict[str, Any]:
    """
    创建模拟的批改结果数据
    
    Args:
        content: 原始文本内容
        score: 分数，如果为None则随机生成
        error_count: 错误数量，如果为None则根据内容长度随机生成
        model: 模拟的模型名称
        
    Returns:
        Dict[str, Any]: 模拟的批改结果数据
    """
    # 计算内容长度和字符数
    content_length = len(content)
    char_count = len([c for c in content if c.strip()])
    
    # 如果未提供分数，则根据内容长度随机生成
    if score is None:
        # 范围在60-95之间的随机分数
        score = random.randint(60, 95)
    
    # 如果未提供错误数量，则根据内容长度随机生成
    if error_count is None:
        # 内容越长，错误可能越多
        base_errors = max(1, content_length // 100)
        error_count = random.randint(base_errors, base_errors * 3)
    
    # 创建错误分析
    error_types = ["语法错误", "拼写错误", "标点错误", "结构错误", "逻辑错误"]
    error_analysis = {}
    
    # 生成随机错误分析
    remaining_errors = error_count
    for error_type in error_types:
        if remaining_errors <= 0:
            break
            
        # 为每种错误类型分配一个随机数量
        count = random.randint(0, remaining_errors)
        if count > 0:
            error_analysis[error_type] = count
            remaining_errors -= count
    
    # 确保至少有一种错误类型
    if not error_analysis and error_count > 0:
        random_type = random.choice(error_types)
        error_analysis[random_type] = error_count
    
    # 生成评语
    comments = []
    if score >= 90:
        comments.append("整体表现优秀，论述清晰有力。")
    elif score >= 80:
        comments.append("整体表现良好，部分内容有待完善。")
    elif score >= 70:
        comments.append("基本达到要求，但存在一些问题需要改进。")
    elif score >= 60:
        comments.append("勉强达到基本要求，有较多问题需要改进。")
    else:
        comments.append("未达到基本要求，需要全面修改。")
    
    # 根据错误分析添加具体评语
    for error_type, count in error_analysis.items():
        if error_type == "语法错误" and count > 0:
            comments.append(f"存在{count}处语法问题，注意主谓一致和时态。")
        elif error_type == "拼写错误" and count > 0:
            comments.append(f"有{count}处拼写错误，建议使用拼写检查工具。")
        elif error_type == "标点错误" and count > 0:
            comments.append(f"有{count}处标点使用不当，请注意标点符号的正确使用。")
        elif error_type == "结构错误" and count > 0:
            comments.append(f"文章结构有{count}处问题，建议调整段落组织。")
        elif error_type == "逻辑错误" and count > 0:
            comments.append(f"存在{count}处逻辑不清晰的地方，论证过程需要加强。")
    
    # 生成改进建议
    improvement_suggestions = [
        "建议增加更多的论据支持你的观点。",
        "可以使用更多的连接词来提高文章的连贯性。",
        "建议采用更加正式的语言风格。",
        "可以增加一些例子来使论点更加具体。",
        "结论部分可以更加明确地呼应开头。"
    ]
    
    # 随机选择2-3条改进建议
    selected_suggestions = random.sample(
        improvement_suggestions,
        min(random.randint(2, 3), len(improvement_suggestions))
    )
    
    # 创建最终结果
    result = {
        "score": score,
        "total_score": score,
        "error_count": error_count,
        "char_count": char_count,
        "comments": " ".join(comments),
        "error_analysis": error_analysis,
        "improvement_suggestions": " ".join(selected_suggestions),
        "processed_at": datetime.now().isoformat(),
        "processing_time": random.uniform(1.5, 5.0),
        "model": model,
        "is_mock": True
    }
    
    return result


def create_mock_deepseek_result(content: str, score: Optional[int] = None) -> Dict[str, Any]:
    """
    创建模拟的Deepseek批改结果
    
    Args:
        content: 原始文本内容
        score: 分数，如果为None则随机生成
        
    Returns:
        Dict[str, Any]: 模拟的Deepseek格式批改结果
    """
    # 获取基础模拟结果
    base_result = create_mock_result(content, score, model="deepseek-reasoner")
    
    # 转换为Deepseek格式
    deepseek_result = {
        "score": base_result["score"],
        "total_score": base_result["score"],
        "feedback": base_result["comments"],
        "error_analysis": base_result["error_analysis"],
        "improvement_suggestions": base_result["improvement_suggestions"],
        "processed_time": base_result["processing_time"],
        "char_count": base_result["char_count"],
        "word_count": base_result["char_count"] // 2,  # 简单估算
        "model": "deepseek-reasoner",
        "is_mock": True,
        "created_at": datetime.now().isoformat()
    }
    
    return deepseek_result 