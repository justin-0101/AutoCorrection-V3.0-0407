#!/usr/bin/env python
# coding: utf-8

import os
import re
import shutil
import sys
from datetime import datetime

def create_backup(filename):
    """创建备份文件"""
    backup_name = f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.copy2(filename, backup_name)
    print(f"已创建备份: {backup_name}")
    return backup_name

def fix_indentation_in_app_py():
    """修复app.py中的缩进和语法问题"""
    filename = "app.py"
    
    # 创建备份
    backup_file = create_backup(filename)
    
    # 读取文件内容
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复docx文件处理中的换行符问题
    content = content.replace("file_content = '\n", "file_content = '\\n")
    
    # 修复函数内游标初始化的缩进
    content = re.sub(
        r'try:\s+conn = get_db\(\)\s+cursor = conn\.cursor\(\)',
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        'try:\n        conn = get_db()\n        cursor = conn.cursor()',
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        content
    )
    
    # 修复.doc处理部分的缩进
    doc_pattern = re.compile(r'elif file_ext == \'.doc\':\s+try:.*?(?=\s+else:)', re.DOTALL)
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    doc_match = doc_pattern.search(content)
    
    if doc_match:
        doc_section = doc_match.group(0)
        # 规范化缩进
        fixed_doc_section = re.sub(r'\n\s{12,}', '\n                        ', doc_section)
        content = content.replace(doc_section, fixed_doc_section)
    
    # 修复批量上传中的缩进问题
    batch_pattern = re.compile(r'@app\.route\(\'/batch_upload\'.*?@app\.route', re.DOTALL)
    batch_match = batch_pattern.search(content)
    
    if batch_match:
        batch_section = batch_match.group(0)
        
        # 修复indent级别
        lines = batch_section.split('\n')
        fixed_lines = []
        
        in_try_block = False
        for line in lines:
            # 处理upload_dir缩进错误
            if 'upload_dir = app.config.get' in line and line.startswith('            '):
                line = '                            ' + line.strip()
            
            # 处理if not os.path.exists缩进错误
            if 'if not os.path.exists' in line and line.startswith('            '):
                line = '                                ' + line.strip()
            
            # 处理os.makedirs缩进错误
            if 'os.makedirs' in line and line.startswith('                '):
                line = '                                    ' + line.strip()

            # 处理content检查的缩进错误
            if 'if not content.strip():' in line:
                line = '                        ' + line.strip()
                in_try_block = True
            elif in_try_block and 'error_message =' in line and not line.startswith('                            '):
                line = '                            ' + line.strip()
                in_try_block = False
            elif in_try_block and 'raise ValueError' in line and not line.startswith('                            '):
                line = '                            ' + line.strip()
                in_try_block = False
                
            # 处理SQL执行的缩进错误
            if 'cursor.execute(' in line and line.startswith('                        '):
                line = '                    ' + line.strip()
            
            # 处理AI评分的缩进错误
            if 'ai_result = unified_ai_scoring' in line and line.startswith('                        '):
                line = '                    ' + line.strip()
                
            fixed_lines.append(line)
        
        fixed_batch_section = '\n'.join(fixed_lines)
        content = content.replace(batch_section, fixed_batch_section)
    
    # 修复membreship部分连接数据库的缩进
    content = content.replace("        conn = sqlite3.connect('instance/essay_correction.db')",
                        "    conn = sqlite3.connect('instance/essay_correction.db')")
    content = content.replace("        cursor = conn.cursor()",
                        "    cursor = conn.cursor()")
    
    # 修复correction函数中if条件的缩进问题
    content = re.sub(
        r'if daily_count >= daily_limit:.*?return redirect\(url_for\(\'membership\'\)\)',
        'if daily_count >= daily_limit:\n                flash(f\'您今日批改已达上限({daily_limit}篇)，请明天再试或升级会员\', \'warning\')\n                return redirect(url_for(\'membership\'))',
        content
    )
    
    content = re.sub(
        r'if monthly_count >= monthly_limit:.*?return redirect\(url_for\(\'membership\'\)\)',
        'if monthly_count >= monthly_limit:\n                flash(f\'您本月批改已达上限({monthly_limit}篇)，请下月再试或升级会员\', \'warning\')\n                return redirect(url_for(\'membership\'))',
        content
    )
    
    # 修复订单历史的缩进和try-except结构
    order_history_pattern = re.compile(r'@app\.route\(\'/order_history\'.*?@app\.route', re.DOTALL)
    order_match = order_history_pattern.search(content)
    
    if order_match:
        order_section = order_match.group(0)
        
        # 修复indent级别和try-except结构
        lines = order_section.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 修复if fetchone下的缩进
            if line.strip().startswith('# 获取总记录数') and not line.startswith('            '):
                line = '            ' + line.strip()
            elif line.strip().startswith('cursor.execute("SELECT COUNT') and not line.startswith('            '):
                line = '            ' + line.strip()
            elif line.strip().startswith('total_orders = cursor.fetchone') and not line.startswith('            '):
                line = '            ' + line.strip()
                
            # 处理else的缩进问题
            if line.strip() == 'else:' and not line.startswith('        '):
                line = '        ' + line.strip()
                
            fixed_lines.append(line)
        
        fixed_order_section = '\n'.join(fixed_lines)
        content = content.replace(order_section, fixed_order_section)
    
    # 修复会员到期日期部分的缩进和try-except结构
    expiry_pattern = re.compile(r'try:\s+# 尝试完整的日期时间格式.*?expiry_date = datetime.now\(\)', re.DOTALL)
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    expiry_match = expiry_pattern.search(content)
    
    if expiry_match:
        expiry_section = expiry_match.group(0)
        # 增加正确的缩进
        fixed_expiry = expiry_section.replace('try:', 'try:')
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        fixed_expiry = fixed_expiry.replace('except ValueError:', '                except ValueError:')
        fixed_expiry = fixed_expiry.replace('try:', '                    try:')
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        
        content = content.replace(expiry_section, fixed_expiry)
    
    # 修复购买会员页面的缩进
    content = content.replace("        return redirect(url_for('membership'))",
                        "    return redirect(url_for('membership'))")
    
    # 保存修复后的文件
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复文件: {filename}")
    print(f"原始文件备份在: {backup_file}")
    print("请运行修复后的app.py检查是否解决了所有问题。")

if __name__ == "__main__":
    print("开始修复app.py中的语法和缩进问题...")
    fix_indentation_in_app_py()
    print("修复完成！") 