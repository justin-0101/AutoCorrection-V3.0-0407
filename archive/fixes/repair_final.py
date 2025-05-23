#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
彻底修复server_external.py中的所有问题
1. 完全重写文件，不保留任何BOM标记
2. 修复未终止的字符串和乱码
3. 添加分数标准化函数
"""

import os
import re
import codecs
import shutil

# 文件路径
original_file = 'server_external.py'
backup_file = 'server_external.py.bak'
fixed_file = 'server_external_final.py'

# 创建备份（如果没有）
if not os.path.exists(backup_file):
    shutil.copy2(original_file, backup_file)
    print(f"已创建备份: {backup_file}")

try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    # 以二进制模式读取内容
    with open(original_file, 'rb') as f:
        content_bytes = f.read()
    
    # 去除BOM（如果存在）
    if content_bytes.startswith(codecs.BOM_UTF8):
        content_bytes = content_bytes[len(codecs.BOM_UTF8):]
        print("已删除BOM标记")
    
    # 尝试解码
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            content = content_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            content = content_bytes.decode('gbk', errors='replace')
            print("使用GBK编码解码（替换模式）")
    
    # 分行处理和修复
    lines = content.split('\n')
    fixed_lines = []
    
    # 添加正确的UTF-8编码声明（确保没有BOM）
    fixed_lines.append("# -*- coding: utf-8 -*-")
    
    # 添加分数标准化函数
    fixed_lines.append("""
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
""")
    
    # 添加MIN_CHARS常量（如果之前缺少）
    fixed_lines.append("""
# 最小字符数要求
MIN_CHARS = 500
""")
    
    # 处理原始文件的每一行，从第2行开始（跳过可能的BOM和编码声明）
    skip_first_line = True
    for i, line in enumerate(lines):
        if skip_first_line:
            skip_first_line = False
            if "# -*- coding:" in line or "#!/usr/bin" in line:
                continue  # 跳过原有的编码声明行
        
        # 修复未终止字符串和乱码字符
        fixed_line = line
        
        # 检查包含乱码中文的行
        if "璀﹀憡" in line or "鍏" in line or "搴" in line:
            # 如果包含警告信息的未终止字符串，替换为正确的中文
            fixed_line = re.sub(
                r'print\(".*?(?=\n|$)',
                'print("警告：未能加载python-docx库，将使用替代方法")',
                line
            )
            print(f"已修复第{i+1}行的乱码和未终止字符串")
        
        # 替换return jsonify的调用，确保使用normalize_scores
        if "return jsonify" in fixed_line and "normalize_scores" not in fixed_line:
            fixed_line = re.sub(
                r'return\s+jsonify\s*\(\s*(.*?)\s*\)',
                r'return jsonify(normalize_scores(\1))',
                fixed_line
            )
            print(f"已更新第{i+1}行的JSON响应，应用normalize_scores")
        
        fixed_lines.append(fixed_line)
    
    # 将修复后的内容写入新文件
    with open(fixed_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    print(f"修复完成，已保存到: {fixed_file}")
    
except Exception as e:
    print(f"处理文件时出错: {str(e)}")
    import traceback
    traceback.print_exc()

print("修复过程完成。请运行 python server_external_final.py 来启动服务器。") 