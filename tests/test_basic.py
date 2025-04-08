#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基本测试脚本
检查测试功能和unittest模块是否正常工作
"""

import unittest
from unittest.mock import MagicMock, patch

class SimpleTest(unittest.TestCase):
    """简单的测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_service = MagicMock()
        self.mock_service.get_value.return_value = "test_value"
    
    def test_basic_assertion(self):
        """测试基本断言功能"""
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)
        self.assertFalse(False)
    
    def test_mock_object(self):
        """测试模拟对象功能"""
        result = self.mock_service.get_value()
        self.assertEqual(result, "test_value")
        self.mock_service.get_value.assert_called_once()
    
    @patch('builtins.print')
    def test_patch_decorator(self, mock_print):
        """测试patch装饰器功能"""
        print("Hello World")
        mock_print.assert_called_once_with("Hello World")

if __name__ == "__main__":
    unittest.main() 