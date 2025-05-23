#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
这个脚本用于修复server_external.py文件的编码问题
1. 移除BOM标记
2. 确保只有一个UTF-8编码声明
3. 添加MIN_CHARS常量定义
4. 修复未终止的字符串
5. 检查未闭合的try块
"""

# 读取原文件内容
with open('server_external.py', 'rb') as f:
    content = f.read()

# 移除BOM标记 (如果存在)
if content.startswith(b'\xef\xbb\xbf'):
    content = content[3:]

# 将内容解码为字符串 (忽略可能的错误)
text = content.decode('utf-8', errors='ignore')

# 找到所有源文件行
lines = text.split('\n')

# 创建新文件内容，从头构建
new_content = ['# -*- coding: utf-8 -*-']

# 跳过可能存在的原有编码声明行
start_idx = 0
for i, line in enumerate(lines):
    if '# -*-' in line or 'coding' in line:
        start_idx = i + 1
    else:
        break

# 检查是否需要添加MIN_CHARS定义
min_chars_defined = False
for line in lines:
    if 'MIN_CHARS' in line and '=' in line:
        min_chars_defined = True
        break

# 如果没有定义MIN_CHARS，添加定义
if not min_chars_defined:
    new_content.append("# 最小字符数要求")
    new_content.append("MIN_CHARS = 500")
    new_content.append("")

# 修复未终止的字符串和未闭合的括号
fixed_lines = []
for i, line in enumerate(lines[start_idx:], start=start_idx):
    if '宸插簲鐢ㄥ熀鏈珻ORS澶?' in line:
        # 特别处理这个错误行
        line = line.replace('宸插簲鐢ㄥ熀鏈珻ORS澶?', '已应用基本CORS配置')
    # 检查字符串是否终止
    if '"' in line and line.count('"') % 2 != 0:
        line = line + '"'
        print(f"修复行 {i+1}: 添加引号")
    # 检查括号是否闭合
    if '(' in line and line.count('(') != line.count(')'):
        line = line + ')'
        print(f"修复行 {i+1}: 添加括号")
    fixed_lines.append(line)

# 添加剩余文件内容
new_content.extend(fixed_lines)

# 检查是否有未完成的try块
try_blocks = 0
except_blocks = 0
try_indices = []
for i, line in enumerate(new_content):
    if line.strip().startswith('try:'):
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        try_blocks += 1
        try_indices.append(i)
    elif line.strip().startswith('except') or line.strip().startswith('finally:'):
        except_blocks += 1
        if try_indices:
            try_indices.pop()

if try_blocks > except_blocks:
    print(f"警告: 检测到 {try_blocks - except_blocks} 个未闭合的try块")
    
    # 尝试修复未闭合的try块
    for idx in try_indices:
        # 找到这个try块下面的缩进级别
        try_line = new_content[idx]
        indent = len(try_line) - len(try_line.lstrip())
        indent_str = ' ' * indent
        
        # 在try块之后添加一个except块
        insert_idx = idx + 1
        while insert_idx < len(new_content) and (not new_content[insert_idx].strip() or len(new_content[insert_idx]) - len(new_content[insert_idx].lstrip()) > indent):
            insert_idx += 1
        
        new_content.insert(insert_idx, f"{indent_str}except Exception as e:")
        new_content.insert(insert_idx + 1, f"{indent_str}    print(f\"错误: {{e}}\")")
        print(f"修复: 在第 {idx+1} 行的try块后添加了except块")

# 写入新文件
with open('server_external_fixed.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_content))

print("修复完成，新文件已保存为 server_external_fixed.py") 