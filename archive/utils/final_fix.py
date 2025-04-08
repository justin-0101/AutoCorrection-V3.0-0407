#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
最终修复脚本 - 专注于去除BOM标记
使用最简单的方法确保没有编码问题
"""

import os
import shutil

# 文件路径
original_file = 'server_external.py'
backup_file = 'server_external.py.bak2'
fixed_file = 'clean_server.py'

# 创建新备份
if not os.path.exists(backup_file):
    shutil.copy2(original_file, backup_file)
    print(f"已创建新备份: {backup_file}")

try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    # 读取原始文件内容
    with open(original_file, 'rb') as f:
        content = f.read()
    
    # 如果以BOM开头，去除它
    if content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
        content = content[3:]
        print("已删除UTF-8 BOM标记")
    
    # 创建新的文件内容
    new_content = b"# -*- coding: utf-8 -*-\n"
    
    # 添加修复函数
    new_content += b"""
# 最小字符数要求
MIN_CHARS = 500

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

    # 添加原始内容（跳过可能的编码声明）
    lines = content.split(b'\n')
    skip_first_lines = 2  # 跳过可能的编码声明行
    for i, line in enumerate(lines):
        if i < skip_first_lines and (b'# -*- coding:' in line or b'#!/usr/bin' in line):
            continue
        else:
            # 修复行中的乱码问题
            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
                line_text = line.decode('utf-8', errors='replace')
                
                # 修复乱码中文提示
                if "璀﹀憡" in line_text or "鍏" in line_text or "搴" in line_text:
                    line_text = line_text.replace(
                        "璀﹀憡锛氭湭鑳藉鍏ython-docx搴", 
                        "警告：未能加载python-docx库"
                    )
                
                # 确保返回的JSON数据使用normalize_scores
                if "return jsonify" in line_text and "normalize_scores" not in line_text:
                    line_text = line_text.replace(
                        "return jsonify(", 
                        "return jsonify(normalize_scores("
                    )
                    if not line_text.endswith("))"):
                        line_text = line_text[:-1] + ")"
                
                new_content += line_text.encode('utf-8') + b'\n'
            except:
                # 如果无法正确解码，保持原样
                new_content += line + b'\n'
    
    # 写入新文件
    with open(fixed_file, 'wb') as f:
        f.write(new_content)
    print(f"修复完成，已保存到: {fixed_file}")
    
except Exception as e:
    print(f"处理文件时出错: {str(e)}")
    import traceback
    traceback.print_exc()

print("最终修复完成。请运行 python clean_server.py 来启动服务器。") 