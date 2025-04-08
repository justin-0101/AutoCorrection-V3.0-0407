#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复BOM标记问题的脚本
将文件以二进制模式读取，移除BOM标记，并以UTF-8编码（不带BOM）保存
"""

import os
import sys
import shutil

def remove_bom(filename, output_filename=None):
    """
    从文件中移除BOM标记
    """
    if output_filename is None:
        output_filename = filename + ".fixed"
    
    # 备份原文件
    backup = filename + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(filename, backup)
        print(f"已创建备份: {backup}")
    
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 以二进制模式读取文件
        with open(filename, 'rb') as f:
            content = f.read()
        
        # 检查是否存在BOM
        has_bom = False
        if content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
            content = content[3:]
            has_bom = True
            print(f"已移除UTF-8 BOM标记")
        
        if not has_bom:
            print(f"文件 {filename} 没有BOM标记")
        
        # 修复其他可能的问题
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 解码为文本
            text = content.decode('utf-8')
            
            # 修复未终止的字符串
            lines = text.split('\n')
            fixed_lines = []
            
            for i, line in enumerate(lines):
                # 修复未终止的字符串和乱码问题
                if "璀﹀憡" in line or "鍏" in line:
                    fixed_line = line.replace(
                        '璀﹀憡锛氭湭鑳藉鍏ython-docx搴擄紝灏嗕娇鐢ㄦ浛浠ｆ柟娉?',
                        '警告：未能加载python-docx库，将使用替代方法")'
                    )
                    print(f"已修复第{i+1}行的乱码和未终止字符串")
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            
            # 重新组合文本
            text = '\n'.join(fixed_lines)
            
            # 添加MIN_CHARS常量（如果缺少）
            if "MIN_CHARS" not in text:
                min_chars_def = "\n# 最小字符数要求\nMIN_CHARS = 500\n"
                # 在导入语句之后插入
                import_end = text.find("import") + 6
                import_end = text.find("\n", import_end)
                text = text[:import_end+1] + min_chars_def + text[import_end+1:]
                print("已添加MIN_CHARS常量")
            
            # 转换回二进制内容
            content = text.encode('utf-8')
        except Exception as e:
            print(f"修复其他问题时出错: {str(e)}")
            print("只移除BOM标记")
        
        # 写入新文件
        with open(output_filename, 'wb') as f:
            f.write(content)
        
        print(f"处理完成，已保存到: {output_filename}")
        return True
    
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    # 获取要处理的文件名
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        output = None
        if len(sys.argv) > 2:
            output = sys.argv[2]
        
        if remove_bom(filename, output):
            print(f"成功移除BOM标记")
    else:
        print("用法: python fix_bom.py <filename> [output_filename]")
        print("示例: python fix_bom.py server_external.py fixed_server.py")
        
        # 默认处理server_external.py
        server_file = "server_external.py"
        if os.path.exists(server_file):
            output = "fixed_server.py"
            print(f"正在处理默认文件: {server_file} -> {output}")
            if remove_bom(server_file, output):
                print(f"\n请运行: python {output}")
        else:
            print(f"默认文件 {server_file} 不存在") 