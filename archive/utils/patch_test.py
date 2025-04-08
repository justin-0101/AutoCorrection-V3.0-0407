# -*- coding: utf-8 -*-
"""
测试评分补丁功能
"""

from scoring_patch import safe_extract_scores, get_string_prompt_template
import json

# 模拟一个AI返回的JSON结果
mock_json = {
    "总得分": 45,  # 注意这是数值类型
    "等级评定": "A-优秀",
    "分项得分": {
        "内容主旨": 22,       # 数值类型
        "语言文采": "17",     # 字符串类型
        "文章结构": 8.5,      # 浮点数类型
        "文面书写": "4.5"     # 字符串类型
    },
    "总体评价": "这是一篇优秀的作文..."
}

print("原始JSON:")
print(json.dumps(mock_json, ensure_ascii=False, indent=2))

# 使用安全提取函数处理分数
scores = safe_extract_scores(mock_json)

print("\n安全提取后的分数(都转为字符串类型):")
print(json.dumps(scores, ensure_ascii=False, indent=2))

# 展示提示模板
print("\n优化后的提示模板(使用字符串表示分数):")
template = get_string_prompt_template()
print(template)

# 最终结果展示
final_result = {
    "success": True,
    "score": scores["total_score"],
    "score_display": f"{scores['total_score']}分",
    "level": scores["level"],
    **scores,
    "comments": "这是一篇很棒的作文",
}

print("\n最终API返回结果:")
print(json.dumps(final_result, ensure_ascii=False, indent=2)) 