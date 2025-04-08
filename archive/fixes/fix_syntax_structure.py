#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复app.py文件中的语法错误，确保try-except结构完整
"""

import os
import re

def fix_syntax_error():
    """修复app.py中的语法错误，特别是第1010-1013行的try-except结构"""
    print("开始修复app.py中的语法错误...")
    
    # 读取app.py文件
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到问题区域 - 大约在第1010行附近
    problem_start = 0
    for i, line in enumerate(lines):
        if "conn.commit()" in line and i >= 1000 and i <= 1020:
            problem_start = i
            break
    
    if problem_start == 0:
        print("未找到问题区域，请手动检查文件")
        return False
    
    # 检查是否存在语法错误 - try块后缺少except或finally
    is_in_try_block = False
    has_except_or_finally = False
    
    for i in range(problem_start, min(problem_start+20, len(lines))):
        line = lines[i].strip()
        # 检查是否有try块
        if "try:" in line:
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            is_in_try_block = True
        # 检查是否有except或finally块
        if "except" in line or "finally:" in line:
            has_except_or_finally = True
            break
        # 如果在try块中遇到return语句
        if is_in_try_block and "return" in line:
            if not has_except_or_finally:
                # 找到问题 - return语句前没有except或finally
                print(f"在第{i+1}行找到问题: return语句前没有except或finally块")
                # 修复 - 将return语句放在try块中
                if i+1 < len(lines) and "except" not in lines[i+1] and "finally:" not in lines[i+1]:
                    # 插入except块
                    lines.insert(i+1, "            except Exception as e:\n")
                    lines.insert(i+2, "                logger.error(f\"重定向到结果页面时出错: {str(e)}\")\n")
                    lines.insert(i+3, "                flash('重定向到结果页面时出错', 'danger')\n")
                    lines.insert(i+4, "                return redirect(url_for('index'))\n")
                    print(f"在第{i+1}行后添加了except块")
                    break
    
    # 写入修改后的内容
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("修复完成!")
    return True

if __name__ == "__main__":
    fix_syntax_error() 