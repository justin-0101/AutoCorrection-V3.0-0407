"""
脚本用于打印完整的统一提示词
"""

from ai_correction_config import get_unified_prompt

# 获取完整提示词
full_prompt = get_unified_prompt("我的梦想", "作文内容...", 650)

# 打印完整提示词
print("\n\n==== 完整的统一提示词 ====\n")
print(full_prompt)
print("\n==== 提示词结束 ====\n")

# 额外信息
print(f"提示词总长度: {len(full_prompt)} 字符") 