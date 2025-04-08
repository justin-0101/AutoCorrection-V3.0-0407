# 测试文件
import unittest
import os
import sys

sys.path.append('.')

try:
    from app.modules_archive_20250408_124637.utils.document_processor import process_document
    print('导入成功')
except Exception as e:
    print(f'导入失败: {str(e)}') 