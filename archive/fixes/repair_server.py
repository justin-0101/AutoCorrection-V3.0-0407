#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复server_external.py中的所有问题
1. 移除BOM标记
2. 修复未终止的字符串
3. 添加分数标准化函数
"""

import os
import re
import codecs
import shutil

# 备份原始文件
original_file = 'server_external.py'
backup_file = 'server_external.py.bak'
fixed_file = 'server_external_repaired.py'

# 创建备份
if not os.path.exists(backup_file):
    shutil.copy2(original_file, backup_file)
    print(f"已创建备份: {backup_file}")

# 读取原始内容，跳过BOM标记
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    # 首先尝试以二进制模式读取
    with open(original_file, 'rb') as f:
        content = f.read()
    
    # 如果存在BOM标记，删除它
    if content.startswith(codecs.BOM_UTF8):
        content = content[len(codecs.BOM_UTF8):]
        print("已删除BOM标记")
    
    # 转换为文本
    content = content.decode('utf-8')
except Exception as e:
    print(f"读取文件错误: {str(e)}")
    exit(1)

# 修复 - 第1部分：处理未终止的字符串
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    # 修复第170行附近的未终止字符串
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 检查包含乱码中文的行
        if "璀﹀憡" in line or "鍏" in line:
            # 修复未终止的字符串
            fixed_line = re.sub(r'print\(".*?(?=\n|$)', 'print("警告：未能加载python-docx库，将使用替代方法")', line)
            fixed_lines.append(fixed_line)
            print(f"已修复第{i+1}行的乱码和未终止字符串")
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
except Exception as e:
    print(f"修复未终止字符串时出错: {str(e)}")
    exit(1)

# 修复 - 第2部分：添加分数标准化函数
score_normalization_code = '''
# 辅助函数：确保分数是字符串类型
def to_string(value):
    """将任何值转换为字符串"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    else:
        return str(value)

# 辅助函数：标准化分数字段
def normalize_scores(result):
    """确保所有分数字段以字符串形式返回"""
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
'''

# 插入分数标准化函数
import_pattern = r'import\s+[\w,\s]+\n\n'
match = re.search(import_pattern, content)
if match:
    insert_position = match.end()
    content = content[:insert_position] + score_normalization_code + '\n' + content[insert_position:]
    print("已添加分数标准化函数")
else:
    print("警告：无法找到合适的位置插入分数标准化函数")
    # 在文件开头添加
    content = "# -*- coding: utf-8 -*-\n" + content
    content = content.replace("# -*- coding: utf-8 -*-", "# -*- coding: utf-8 -*-" + score_normalization_code)

# 修复 - 第3部分：更新所有返回JSON的地方，使用normalize_scores函数
# 找到所有return jsonify()的行
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    # 保守地修改，确保在原始函数逻辑之后调用normalize_scores
    content = re.sub(
        r'return\s+jsonify\s*\(\s*(.*?)\s*\)',
        r'return jsonify(normalize_scores(\1))',
        content
    )
    print("已更新所有JSON响应应用normalize_scores")
except Exception as e:
    print(f"更新JSON响应时出错: {str(e)}")

# 保存修复后的文件
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    with open(fixed_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"修复完成，已保存到: {fixed_file}")
except Exception as e:
    print(f"保存文件错误: {str(e)}")
    exit(1)

print("修复过程完成。请运行 python server_external_repaired.py 来启动服务器。") 