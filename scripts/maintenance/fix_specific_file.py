#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
专门用于修复tasks/correction_tasks.py文件的脚本
"""

import os
import sys
import binascii
from app.core.services.file_service import FileService

def fix_specific_file(file_path):
    """
    直接使用二进制方式修复指定文件中的所有null字节和其他特殊字符
    """
    # 确保文件存在
    file_service = FileService()
    if not file_service.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return False
    
    try:
        # 读取文件的二进制内容
        with file_service.open(file_path, 'rb') as file:
            content = file.read()
        
        # 备份原始文件
        backup_path = file_path + '.bak'
        with file_service.open(backup_path, 'wb') as backup_file:
            backup_file.write(content)
        print(f"已创建备份文件: {backup_path}")
        
        # 打印文件的前100个字节的十六进制表示
        print(f"文件前100个字节: {binascii.hexlify(content[:100])}")
        
        # 检查是否包含null字节
        null_count = content.count(b'\x00')
        print(f"文件中包含 {null_count} 个null字节")
        
        # 替换所有null字节和可能的问题字符
        cleaned_content = content
        for bad_byte in [b'\x00', b'\xff', b'\xfe', b'\xef\xbb\xbf']:
            if bad_byte in cleaned_content:
                print(f"替换字节: {binascii.hexlify(bad_byte)}")
                cleaned_content = cleaned_content.replace(bad_byte, b'')
        
        # 创建全新的文件而不是覆盖原文件
        new_file_path = file_path + '.new'
        with file_service.open(new_file_path, 'wb') as new_file:
            new_file.write(cleaned_content)
        print(f"已创建新文件: {new_file_path}")
        
        # 删除原文件并将新文件重命名
        file_service.remove(file_path)
        file_service.rename(new_file_path, file_path)
        print(f"已替换原文件: {file_path}")
        
        return True
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    # 要修复的目标文件
    target_file = 'tasks/correction_tasks.py'
    
    print(f"开始修复文件: {target_file}")
    success = fix_specific_file(target_file)
    
    if success:
        print(f"成功处理文件: {target_file}")
    else:
        print(f"修复文件失败: {target_file}")
    
    # 如果第一个文件存在，也修复这个文件
    app_task_file = 'app/tasks/correction_tasks.py'
    if os.path.exists(app_task_file):
        print(f"\n开始修复文件: {app_task_file}")
        success = fix_specific_file(app_task_file)
        
        if success:
            print(f"成功处理文件: {app_task_file}")
        else:
            print(f"修复文件失败: {app_task_file}")
    
    print("\n完成。请重启应用程序查看问题是否解决。") 