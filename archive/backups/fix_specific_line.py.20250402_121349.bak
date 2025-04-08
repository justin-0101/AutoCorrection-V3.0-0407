#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
这个脚本专门用于修复server_external_fixed.py文件中的第154行
"""

with open('server_external_fixed.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 检查并修复特定行
if len(lines) >= 154:
    print(f"原始第154行: {lines[153].strip()}")
    if '已应用基本CORS配置' in lines[153] and not lines[153].strip().endswith('"'):
        # 修复未终止的字符串
        lines[153] = 'print("已应用基本CORS配置")\n'
        print(f"修复后第154行: {lines[153].strip()}")

# 写回文件
with open('server_external_fixed.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("修复完成") 