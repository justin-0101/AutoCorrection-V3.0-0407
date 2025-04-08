#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试运行脚本
设置正确的Python路径并运行测试
"""

import os
import sys
import unittest
import importlib

# 获取当前文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 添加项目根目录到Python路径
root_dir = current_dir
sys.path.insert(0, root_dir)

# 设置环境变量
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'

def run_unit_tests():
    """
    运行单元测试
    """
    print("\n=========== 正在运行单元测试 ===========\n")
    
    # 发现并运行所有单元测试
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests/unit', pattern='test_*.py')
    test_runner = unittest.TextTestRunner(verbosity=2)
    
    try:
        result = test_runner.run(test_suite)
        return result.wasSuccessful()
    except ImportError as e:
        print(f"导入错误: {e}")
        return False

def run_integration_tests():
    """
    运行集成测试
    """
    print("\n=========== 正在运行集成测试 ===========\n")
    
    # 发现并运行所有集成测试
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests/integration', pattern='test_*.py')
    test_runner = unittest.TextTestRunner(verbosity=2)
    
    try:
        result = test_runner.run(test_suite)
        return result.wasSuccessful()
    except ImportError as e:
        print(f"导入错误: {e}")
        return False

def run_individual_test_file(file_path):
    """
    运行单个测试文件
    
    Args:
        file_path: 测试文件路径，相对于项目根目录
    """
    print(f"\n=========== 正在运行测试文件: {file_path} ===========\n")
    
    # 将文件路径转换为模块名
    module_path = file_path.replace('/', '.').replace('\\', '.')
    if module_path.endswith('.py'):
        module_path = module_path[:-3]
    
    try:
        # 加载并运行测试模块
        test_module = importlib.import_module(module_path)
        test_suite = unittest.TestLoader().loadTestsFromModule(test_module)
        test_runner = unittest.TextTestRunner(verbosity=2)
        result = test_runner.run(test_suite)
        return result.wasSuccessful()
    except ImportError as e:
        print(f"导入错误: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='运行测试')
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--file', type=str, help='运行单个测试文件')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    
    args = parser.parse_args()
    
    success = True
    
    print("Python环境路径:")
    for p in sys.path:
        print(f" - {p}")
    
    if args.unit or args.all:
        unit_success = run_unit_tests()
        success = success and unit_success
    
    if args.integration or args.all:
        integration_success = run_integration_tests()
        success = success and integration_success
    
    if args.file:
        file_success = run_individual_test_file(args.file)
        success = success and file_success
    
    if not (args.unit or args.integration or args.file or args.all):
        # 如果没有提供参数，运行单元测试
        success = run_unit_tests()
    
    # 设置退出码
    sys.exit(0 if success else 1) 