#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改系统AI评分配置文件
集中存放所有与AI评分相关的设置、提示词模板和评分标准
"""

import json
import logging
import os
from tasks import task_unified_scoring  # 导入统一评分任务

# 设置日志
logger = logging.getLogger(__name__)

# AI模型相关设置
AI_SETTINGS = {
    "temperature": 0.1,          # 温度参数，越低结果越确定性
    "max_tokens": 4000,          # 最大生成token数
    "timeout_seconds": 60,       # API调用超时时间（秒）
    "retry_count": 2,            # 失败重试次数
    "retry_delay": 2,            # 重试延迟（秒）
}

# 评分标准和权重设置
SCORING = {
    "total_points": 50,          # 总分值
    "min_word_count": 600,       # 最小字数要求
    "grades": {                  # 等级划分
        "A": {"min": 43, "max": 50, "label": "A-优秀"},
        "B": {"min": 35, "max": 42, "label": "B-良好"},
        "C": {"min": 27, "max": 34, "label": "C-中等"},
        "D": {"min": 0, "max": 26, "label": "D-不足"}
    },
    "criteria": {                # 评分维度及分值范围
        "content": {"min": 0, "max": 20, "name": "内容主旨"},
        "language": {"min": 0, "max": 15, "name": "语言文采"},
        "structure": {"min": 0, "max": 10, "name": "文章结构"},
        "writing": {"min": 0, "max": 5, "name": "文面书写"}
    },
    "deductions": {              # 扣分项
        "typo": 1,               # 每个错别字扣分
        "no_title": 2,           # 无标题扣分
        "insufficient_words": 1  # 字数不足每少50字扣1分
    }
}

# 提示词模板
def get_prompt_template(subject, text, text_length):
    """
    生成评分提示词模板
    
    Args:
        subject (str): 作文标题
        text (str): 作文内容（可能会被截断）
        text_length (int): 原始文本长度
        
    Returns:
        str: 完整提示词
    """
    # 基础提示词 - 任务描述和作文信息
    prompt_start = f"""<请你作为广东中考语文阅卷老师，按照以下标准对作文进行全面评分和详细分析：

作文标题：{subject if subject else "无标题"}
作文内容：{text[:3000]}...（内容过长已省略）
字数：{text_length}字

【广东中考语文作文评分标准】
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

请依据作文质量给予合理的各项得分。注意：对于质量较差的作文，各项分数应相应降低，四项得分总和可以小于50分。

【具体扣分项】
1. 无标题扣2分
2. 字数不足：低于600字，每少50字扣1分
3. 错别字：每个错别字扣1分
4. 标点符号使用不规范：根据严重程度1-3分

错别字扣分是从四项得分总和中直接扣除的，而非从某个分项中扣除。

【错别字识别指南】
1. 仔细检查全文，特别关注易错字、形近字、音近字
2. 重点检查专有名词、成语、特殊词汇的拼写
3. 注意辨别同音字、多音字的正确使用
4. 区分正确的异体字和错误的别字
5. 标记每个错别字的位置（段落句子）、错误写法、正确写法和上下文"""

    # JSON格式返回指令
    json_instructions = """
必须以JSON格式返回结果，结构如下：
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
"扣分": {
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

【重要提示】
1. 所有分数必须是整数（不要小数点），以字符串形式返回
2. 根据作文质量给分，质量差的文章各项分数应降低，四项得分总和可以小于50分
3. 确保内容分不超过20分、语言分不超过15分、结构分不超过10分、书写分不超过5分
4. 总得分 = 四项得分之和 - 错别字扣分
5. 错别字扣分为：错别字数量 × 1分/个
6. 详细列出所有发现的错别字
7. 所有分析内容务必详尽完整，包括总体评价、内容分析、语言分析、结构分析等
"""

    # 返回完整提示词
    return prompt_start + json_instructions

# 新增统一评分提示词模板
def get_unified_prompt(subject, text, text_length):
    """
    生成统一的作文评分提示词，整合所有评分维度
    
    Args:
        subject (str): 作文标题
        text (str): 作文内容
        text_length (int): 作文字数
        
    Returns:
        str: 包含所有评分维度的统一提示词
    """
    # 动态生成评分规则
    criteria = "\n".join([
        f"- {v['name']}：{v['min']}-{v['max']}分" 
        for v in SCORING["criteria"].values()
    ])
    
    # 构建完整提示词
    prompt = f"""
    <作为广东中考语文阅卷专家，请一次性完成以下所有分析：
    
    【作文信息】
    标题：{subject or "无标题"}
    字数：{text_length}字（{'内容过长已截断' if len(text) > 3000 else '完整内容'}）
    内容预览：{text[:3000]}{'...' if len(text) > 3000 else ''}
    
    【评分规则】
    总分50分，分项得分范围：
    {criteria}
    
    【必须完成的分析维度】
    1. 错别字检测：逐句扫描，标注错误位置及正确写法
    2. 内容主旨：分析论点、论据与主题的契合度
    3. 表达文采：识别修辞手法（至少3种）和语言特色
    4. 文章结构：评估开头、过渡、结尾的逻辑性
    5. 文面书写：检查标点使用和卷面整洁度
    
    【输出格式说明】
    必须严格按照以下JSON结构输出，确保字段名称完全一致：
    - "总得分"：一个表示总分的字符串，如"45"
    - "等级评定"：一个表示等级的字符串，如"A-优秀"
    - "分项得分"：一个包含四个子字段的对象
    - "内容主旨"："18"（范围0-20分）
    - "语言文采"："14"（范围0-15分）
    - "文章结构"："9"（范围0-10分）
    - "文面书写"："4"（范围0-5分）
    - "错别字"：一个包含错别字信息的数组
    - "多维分析"：一个包含四个子字段的对象
    - "内容分析"：文本字符串（内容分析结果）
    - "表达分析"：文本字符串（表达分析结果）
    - "结构分析"：文本字符串（结构分析结果）
    - "书写分析"：文本字符串（书写分析结果）
    - "总体评价"：文本字符串（总体评价结果）
    
    【特别注意】
    1. 务必确保JSON中的字段名称正确无误
    2. 各项分数必须是整数，作为字符串返回
    3. 请提供详尽的分析内容，特别是各个维度的分析
    
    【输出格式】
    严格使用以下JSON结构（字段名不可更改）：
    {task_unified_scoring.format_instruction()}
    """
    return prompt

# 备用评分结果
def get_fallback_result(subject, text):
    """
    当AI评分失败时的备用评分结果
    
    Args:
        subject (str): 作文标题
        text (str): 作文内容
        
    Returns:
        dict: 备用评分结果
    """
    return {
        'id': 999,
        'title': subject or "无标题作文",
        'content': text,
        'submission_time': "", # 需要在使用时填入当前时间
        'word_count': len(text),
        'total_score': 40,
        'grade': 'B-良好',
        'content_score': 18,
        'language_score': 12,
        'structure_score': 8,
        'writing_score': 2,
        'error_count': 0,
        'errors': [],
        'overall_assessment': '这是一篇良好的作文，内容充实，观点明确，语言表达流畅。有一些小的瑕疵，但整体水平很好。',
        'content_analysis': '文章主题突出，围绕中心思想展开论述，观点明确。论据较为充分，但部分论述可以更加深入。建议在例证上增加一些具体细节，使论证更有说服力。',
        'language_analysis': '语言表达流畅，用词较为准确，句式多样。有一些词语使用不够精准，建议注意词语的准确性和表达的多样性。增加一些修辞手法会使文章更加生动。',
        'structure_analysis': '文章结构完整，有明确的开头、主体和结尾。段落之间过渡自然，层次清晰。建议进一步优化段落间的逻辑关系，使文章结构更加严密。',
        'writing_analysis': '书写整洁，标点符号使用正确。注意个别字的书写规范，保持字体大小的一致性。'
    }

# 统一错别字处理函数
def extract_spelling_errors(result_json):
    """
    从AI返回的JSON中统一提取错别字信息
    
    Args:
        result_json (dict): AI返回的原始JSON结果
        
    Returns:
        list: 错别字列表
    """
    spelling_errors = []
    
    # 尝试从各种可能的位置获取错别字
    if "扣分" in result_json:
        if "错别字" in result_json["扣分"]:
            spelling_errors = result_json["扣分"]["错别字"]
        elif "错别字分" in result_json["扣分"]:
            spelling_errors = result_json["扣分"]["错别字分"]
    
    # 也尝试从顶层字段获取
    if not spelling_errors and "错别字分" in result_json:
        spelling_errors = result_json["错别字分"]
    
    return spelling_errors if isinstance(spelling_errors, list) else []

# 格式化错别字详情为可读文本
def format_spelling_errors(errors):
    """
    将错别字列表格式化为可读文本
    
    Args:
        errors (list): 错别字字典列表
        
    Returns:
        str: 格式化后的错别字描述文本
    """
    if not errors:
        return "未发现错别字"
    
    details = []
    for error in errors:
        if isinstance(error, dict):
            wrong = error.get('错误', '')
            correct = error.get('正确写法', '')
            position = error.get('位置', '')
            detail = f"【{wrong}】应为【{correct}】，位置：{position}"
            details.append(detail)
    
    if not details:
        return f"发现{len(errors)}个错别字，但无法提取详细信息"
    
    return f"发现{len(errors)}个错别字：" + "；".join(details)

# 检查和修正各项分数的分配
def normalize_scores(result, session_id="unknown"):
    """
    标准化分数和评分数据结构
    """
    # 处理分项得分为整数
    if "分项得分" in result and isinstance(result["分项得分"], dict):
        for key, value in result["分项得分"].items():
            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
                result["分项得分"][key] = int(value)
            except (ValueError, TypeError):
                pass  # 保持原样
                
    # 保持原始评级
    if "总得分" in result:
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            total_score = int(result["总得分"])
            # 只添加兼容性字段，不修改原字段
            result["total_score"] = total_score
        except (ValueError, TypeError):
            pass
            
    # 保持原始等级评定
    if "等级评定" in result:
        grade = result["等级评定"]
        result["grade"] = grade  # 添加兼容性字段
        
    # 保持错别字数据不变
    return result 