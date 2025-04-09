#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查看批改服务日志
以正确的编码显示日志内容
"""

import os
import sys
import codecs

# 确保工作目录正确
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
log_file = os.path.join(project_root, 'logs', 'correction_service.log')

def view_log(file_path, lines=50):
    """查看指定文件的最后几行"""
    if not os.path.exists(file_path):
        print(f"错误：日志文件不存在 {file_path}")
        return
    
    # 尝试不同的编码
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
    all_lines = []
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                all_lines = f.readlines()
                print(f"成功使用 {encoding} 编码读取日志文件")
                break
        except Exception as e:
            print(f"使用 {encoding} 编码读取失败: {str(e)}")
    
    if not all_lines:
        print("无法使用任何编码读取日志文件")
        return
    
    # 获取最后指定行数
    last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
    
    print(f"\n查看最后 {len(last_lines)} 行日志 ({file_path}):\n")
    print("=" * 80)
    for line in last_lines:
        print(line.strip())
    print("=" * 80)

def main():
    """主函数"""
    if len(sys.argv) > 1:
        try:
            lines = int(sys.argv[1])
        except ValueError:
            print("参数必须是一个整数，表示要查看的行数")
            return
    else:
        lines = 50  # 默认显示最后50行
    
    view_log(log_file, lines)

if __name__ == "__main__":
    main() 