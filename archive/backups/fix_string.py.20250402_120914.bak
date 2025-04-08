#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复未终止字符串问题的脚本
"""

import re

# 文件路径
input_file = "final_fixed.py"
output_file = "server_ready.py"

# 读取文件内容
with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

fixed_lines = []
for i, line in enumerate(lines):
    # 修复未终止的字符串
    if '璀﹀憡' in line or '鍏' in line or '搴' in line:
        # 对于每个包含乱码的行
        if 'print(' in line or 'print (' in line:
            # 确保print语句正确终止
            fixed_line = re.sub(
                r'print\s*\(\s*".*', 
                'print("警告：未能加载python-docx库，将使用替代方法")', 
                line
            )
            print(f"已修复第{i+1}行的未终止字符串: {line.strip()}")
            fixed_lines.append(fixed_line)
        else:
            # 其他乱码行，简单替换为空行或注释
            fixed_line = "# 此行包含乱码，已被注释\n"
            print(f"已注释第{i+1}行的乱码内容")
            fixed_lines.append(fixed_line)
    else:
        fixed_lines.append(line)

# 添加MIN_CHARS常量（如果不存在）
has_min_chars = False
for line in fixed_lines:
    if 'MIN_CHARS' in line:
        has_min_chars = True
        break

if not has_min_chars:
    # 在导入语句后添加MIN_CHARS定义
    for i, line in enumerate(fixed_lines):
        if line.startswith('import') or 'from ' in line:
            last_import_idx = i
    
    min_chars_def = "\n# 最小字符数要求\nMIN_CHARS = 500\n"
    fixed_lines.insert(last_import_idx + 1, min_chars_def)
    print("已添加MIN_CHARS常量定义")

# 写入修复后的内容
with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print(f"处理完成，已保存到: {output_file}")
print(f"请使用命令运行: python {output_file}") 