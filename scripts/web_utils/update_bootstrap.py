#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
更新所有HTML文件中的Bootstrap引用
"""

import os
import sys
import re
from pathlib import Path
import shutil

print("开始执行Bootstrap引用更新脚本...")

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent
APP_TEMPLATES_DIR = ROOT_DIR / "app" / "templates"
TEMPLATES_DIR = ROOT_DIR / "templates"

print(f"工作目录: {ROOT_DIR}")
print(f"应用模板目录: {APP_TEMPLATES_DIR}")
print(f"总模板目录: {TEMPLATES_DIR}")

# 要查找并替换的模式
PATTERNS_TO_REPLACE = [
    # Bootstrap CSS CDN 替换
    {
        "old": r'<link\s+href="https:\/\/cdn\.jsdelivr\.net\/npm\/bootstrap@5\.[0-9.]+\/dist\/css\/bootstrap\.min\.css"\s+rel="stylesheet">',
        "new": '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">'
    },
    # Bootstrap Icons CDN 替换
    {
        "old": r'<link\s+href="https:\/\/cdn\.jsdelivr\.net\/npm\/bootstrap-icons@[0-9.]+\/font\/bootstrap-icons\.(?:min\.)?css"\s+rel="stylesheet">',
        "new": '<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">'
    },
    # 本地Bootstrap CSS替换
    {
        "old": r'<link\s+rel="stylesheet"\s+href="\{\{\s*url_for\(\'static\'\s*,\s*filename=\'css\/bootstrap\.min\.css\'\)\s*\}\}">',
        "new": '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/bootstrap.min.css\') }}">'
    },
    # 本地Bootstrap Icons替换
    {
        "old": r'<link\s+rel="stylesheet"\s+href="\{\{\s*url_for\(\'static\'\s*,\s*filename=\'css\/bootstrap-icons\.(?:min\.)?css\'\)\s*\}\}">',
        "new": '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/bootstrap-icons.min.css\') }}">'
    },
    # 预加载Bootstrap CSS替换
    {
        "old": r'<link\s+rel="preload"\s+href="\{\{\s*url_for\(\'static\'\s*,\s*filename=\'css\/bootstrap\.min\.css\'\)\s*\}\}"\s+as="style">',
        "new": '<link rel="preload" href="{{ url_for(\'static\', filename=\'css/bootstrap.min.css\') }}" as="style">'
    },
    # 预加载Bootstrap Icons替换
    {
        "old": r'<link\s+rel="preload"\s+href="\{\{\s*url_for\(\'static\'\s*,\s*filename=\'css\/bootstrap-icons\.(?:min\.)?css\'\)\s*\}\}"\s+as="style">',
        "new": '<link rel="preload" href="{{ url_for(\'static\', filename=\'css/bootstrap-icons.min.css\') }}" as="style">'
    }
]

def find_html_files(directory):
    """查找目录中的所有HTML文件"""
    html_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))
    return html_files

def update_file(file_path):
    """更新文件中的Bootstrap引用"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 应用替换
        for pattern in PATTERNS_TO_REPLACE:
            content = re.sub(pattern["old"], pattern["new"], content)
        
        # 如果内容有变化，保存文件
        if content != original_content:
            # 备份
            backup_path = str(file_path) + ".bak"
            shutil.copy2(file_path, backup_path)
            
            # 保存修改后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"已更新文件: {file_path} (已备份到 {backup_path})")
            return True
        else:
            print(f"文件未变更: {file_path}")
            return False
    
    except Exception as e:
        print(f"处理文件时出错 {file_path}: {str(e)}")
        return False

def main():
    """主函数"""
    print("开始更新HTML文件中的Bootstrap引用...")
    
    # 查找所有HTML文件
    app_html_files = find_html_files(APP_TEMPLATES_DIR)
    templates_html_files = find_html_files(TEMPLATES_DIR)
    all_html_files = app_html_files + templates_html_files
    
    print(f"找到 {len(all_html_files)} 个HTML文件")
    
    # 更新文件
    updated_count = 0
    for file_path in all_html_files:
        if update_file(file_path):
            updated_count += 1
    
    print(f"\n更新完成! 共更新 {updated_count}/{len(all_html_files)} 个文件")
    
    if updated_count > 0:
        print("请重启Flask应用以应用更改")

if __name__ == "__main__":
    main() 