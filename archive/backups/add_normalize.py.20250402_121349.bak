#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
添加normalize_scores函数并在JSON响应中应用它
"""

import re

# 文件路径
input_file = "server_ready.py"
output_file = "server_final.py"

# 读取文件内容
with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加normalize_scores函数（如果不存在）
normalize_function = """
# 辅助函数：确保分数是字符串类型
def to_string(value):
    \"\"\"将任何值转换为字符串\"\"\"
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    else:
        return str(value)

# 辅助函数：标准化分数字段
def normalize_scores(result):
    \"\"\"确保所有分数字段以字符串形式返回\"\"\"
    if not isinstance(result, dict):
        return result
        
    score_fields = [
        'content_score', 'language_score', 'structure_score', 
        'writing_score', 'total_score', '总分'
    ]
    
    for field in score_fields:
        if field in result and result[field] is not None:
            result[field] = to_string(result[field])
            
    # 处理分项得分
    if 'sub_item_scores' in result and isinstance(result['sub_item_scores'], dict):
        for key, value in result['sub_item_scores'].items():
            result['sub_item_scores'][key] = to_string(value)
    
    # 处理分项得分的中文版本
    if '分项得分' in result and isinstance(result['分项得分'], dict):
        for key, value in result['分项得分'].items():
            result['分项得分'][key] = to_string(value)
    
    return result
"""

if "def normalize_scores" not in content:
    # 在import语句之后插入函数
    import_pattern = r'(from\s+[\w.]+\s+import\s+.*\n|import\s+[\w.]+.*\n)+'
    match = re.search(import_pattern, content)
    if match:
        pos = match.end()
        content = content[:pos] + "\n" + normalize_function + "\n" + content[pos:]
        print("已添加normalize_scores函数")
    else:
        # 在文件开头添加
        content = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n\n" + normalize_function + "\n" + content
        print("已在文件开头添加normalize_scores函数")

# 2. 确保所有jsonify调用都应用normalize_scores
modified_content = re.sub(
    r'return\s+jsonify\s*\(\s*([^)]+)\s*\)', 
    r'return jsonify(normalize_scores(\1))', 
    content
)

if modified_content != content:
    content = modified_content
    print("已更新所有jsonify调用，应用normalize_scores函数")
else:
    print("所有jsonify调用已经使用normalize_scores函数")

# 3. 写入修改后的内容
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"处理完成，已保存到: {output_file}")
print(f"请使用命令运行: python {output_file}") 