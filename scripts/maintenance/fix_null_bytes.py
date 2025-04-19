#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to fix null bytes in Python files
"""

import os
import sys
import re
from app.core.services.file_service import FileService

def fix_file(file_path):
    """Fix null bytes in the specified file using direct binary manipulation."""
    try:
        file_service = FileService()
        # 读取文件的二进制内容
        with file_service.open(file_path, 'rb') as file:
            content = file.read()
        
        # 检查是否有null字节（0x00）或其他问题字符
        has_null_bytes = b'\x00' in content
        has_xff_bytes = b'\xff' in content
        
        if has_null_bytes or has_xff_bytes:
            print(f"Found problematic bytes in {file_path}")
            
            # 替换所有的null字节和0xFF字节
            cleaned_content = content.replace(b'\x00', b'').replace(b'\xff', b'')
            
            # 在Windows环境中使用'wb'模式写入文件
            with file_service.open(file_path, 'wb') as file:
                file.write(cleaned_content)
            
            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No null bytes found in {file_path}")
            return False
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False

def scan_directory(directory):
    """Recursively scan directory for Python files and fix null bytes."""
    fixed_count = 0
    total_count = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_count += 1
                if fix_file(file_path):
                    fixed_count += 1
                    
    return fixed_count, total_count

def find_import_paths(file_path):
    """分析Python文件并寻找导入的模块路径"""
    try:
        file_service = FileService()
        with file_service.open(file_path, 'rb') as file:
            content = file.read()
            
        # 转换为文本以分析导入语句
        text_content = content.decode('utf-8', errors='ignore')
        
        # 使用正则表达式查找import语句
        import_patterns = [
            r'from\s+([a-zA-Z0-9_.]+)\s+import',  # from X import Y
            r'import\s+([a-zA-Z0-9_.]+)'          # import X
        ]
        
        imported_modules = []
        for pattern in import_patterns:
            for match in re.finditer(pattern, text_content):
                module_path = match.group(1)
                imported_modules.append(module_path)
        
        return imported_modules
    except Exception as e:
        print(f"Error analyzing imports in {file_path}: {str(e)}")
        return []

def convert_import_to_file_path(import_path):
    """将导入路径转换为文件路径"""
    return import_path.replace('.', '/') + '.py'

if __name__ == "__main__":
    # 首先修复tasks目录下的问题文件
    task_dirs = ['tasks', 'app/tasks']
    
    for task_dir in task_dirs:
        if os.path.exists(task_dir):
            print(f"\n检查目录: {task_dir}")
            scan_directory(task_dir)
    
    # 特别关注的文件
    problem_files = [
        'tasks/correction_tasks.py', 
        'app/tasks/correction_tasks.py',
        'services/ai_service.py',
        'app/core/ai/ai_service.py'
    ]
    
    print("\n单独检查重要文件:")
    for file_path in problem_files:
        if file_service.exists(file_path):
            fix_file(file_path)
            
            # 分析这个文件导入的其他模块
            print(f"检查 {file_path} 导入的模块...")
            imported_modules = find_import_paths(file_path)
            for module in imported_modules:
                potential_file = convert_import_to_file_path(module)
                if file_service.exists(potential_file):
                    print(f"检查导入的模块文件: {potential_file}")
                    fix_file(potential_file)
        else:
            print(f"File not found: {file_path}")
            
    print("\n完成。请重启应用程序查看问题是否解决。") 