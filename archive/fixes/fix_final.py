#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
最终修复脚本 - 修复server_external.py的BOM标记问题
并修复server_external_fixed.py的未终止字符串问题
"""
import re

# 修复server_external.py文件
print("正在修复server_external.py...")
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    # 以二进制模式读取文件
    with open('server_external.py', 'rb') as f:
        content = f.read()
    
    # 检查并移除BOM标记
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
        print("已移除BOM标记")
    
    # 将内容写回文件，确保使用UTF-8编码，无BOM
    with open('server_external_final.py', 'wb') as f:
        # 添加UTF-8编码声明作为第一行
        f.write(b'# -*- coding: utf-8 -*-\n')
        # 写入其余内容（跳过原始文件中可能的编码声明行）
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            text = content.decode('utf-8')
            lines = text.split('\n')
            skip_first_line = False
            if '# -*- coding:' in lines[0] or '# coding=' in lines[0]:
                skip_first_line = True
                print("跳过原文件中的编码声明行")
            
            if skip_first_line:
                content = '\n'.join(lines[1:]).encode('utf-8')
            
            f.write(content)
            print("已成功保存修复后的文件: server_external_final.py")
        except UnicodeDecodeError:
            print("警告: 解码失败，直接写入原始内容")
            f.write(content)
except Exception as e:
    print(f"修复server_external.py时出错: {e}")

# 修复server_external_fixed.py文件的未终止字符串
print("\n正在修复server_external_fixed.py...")
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    with open('server_external_fixed.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 修复行号从0开始，所以第155行是lines[154]
    if len(lines) >= 155:
        problematic_line = lines[154]
        print(f"问题行: {problematic_line.strip()}")
        
        # 检查并修复未终止的字符串
        if '"' in problematic_line and problematic_line.count('"') % 2 != 0:
            # 如果是未终止的字符串，添加缺失的引号
            lines[154] = problematic_line.rstrip() + '"\n'
            print(f"已修复为: {lines[154].strip()}")
        
        # 写回修复后的内容
        with open('server_external_fixed2.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print("已成功保存修复后的文件: server_external_fixed2.py")
except Exception as e:
    print(f"修复server_external_fixed.py时出错: {e}")

print("\n修复完成，请尝试运行server_external_final.py或server_external_fixed2.py") 