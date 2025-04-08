#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单处理BOM标记的直接脚本
不添加任何额外代码，仅删除BOM标记
"""

import os

# 文件路径
input_file = "server_external.py"
output_file = "final_fixed.py"

# 以二进制模式读取文件
with open(input_file, 'rb') as f:
    content = f.read()

# 检查并删除BOM标记
if content.startswith(b'\xef\xbb\xbf'):
    content = content[3:]
    print("已删除BOM标记")

# 以二进制模式写入文件
with open(output_file, 'wb') as f:
    f.write(content)

print(f"处理完成，已保存到: {output_file}")
print(f"请使用命令运行: python {output_file}") 