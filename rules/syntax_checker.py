#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
语法检查工具 - 专门检查项目中的缩进和try-except结构问题

此脚本可以扫描项目中的Python文件，检查常见的语法问题，
特别关注缩进错误和try-except结构不完整的情况。
"""

import os
import sys
import ast
import tokenize
import io
import re
import logging
from typing import List, Dict, Tuple, Optional, Set

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('syntax_check.log', 'w', 'utf-8')
    ]
)
logger = logging.getLogger(__name__)

class SyntaxChecker:
    """语法检查器，用于检查Python文件中的各种语法问题"""
    
    def __init__(self, project_path: str, exclude_dirs: Optional[List[str]] = None):
        """
        初始化语法检查器
        
        Args:
            project_path: 要检查的项目路径
            exclude_dirs: 要排除的目录列表
        """
        self.project_path = os.path.abspath(project_path)
        self.exclude_dirs = exclude_dirs or ['venv', 'env', '.venv', '.env', '__pycache__', 'node_modules']
        self.issues_found = 0
    
    def find_python_files(self) -> List[str]:
        """
        递归查找项目中的所有Python文件
        
        Returns:
            Python文件路径列表
        """
        python_files = []
        
        for root, dirs, files in os.walk(self.project_path):
            # 排除指定目录
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def check_indentation(self, file_path: str) -> List[Dict]:
        """
        检查文件中的缩进问题
        
        Args:
            file_path: 要检查的文件路径
            
        Returns:
            包含缩进问题信息的字典列表
        """
        issues = []
        
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 检查每一行的缩进
            for i, line in enumerate(lines):
                # 跳过空行和注释行
                if not line.strip() or line.strip().startswith('#'):
                    continue
                
                # 检查缩进是否为4的倍数
                leading_spaces = len(line) - len(line.lstrip())
                if leading_spaces % 4 != 0:
                    issues.append({
                        'line': i + 1,
                        'type': 'indentation',
                        'message': f'缩进不是4的倍数 (有{leading_spaces}个空格)'
                    })
                
                # 检查是否混用了空格和制表符
                if '\t' in line[:leading_spaces]:
                    issues.append({
                        'line': i + 1,
                        'type': 'indentation',
                        'message': '混用了空格和制表符'
                    })
        except Exception as e:
            logger.error(f"检查文件 {file_path} 的缩进时出错: {str(e)}")
        
        return issues
    
    def check_try_except_structure(self, file_path: str) -> List[Dict]:
        """
        检查try-except结构的完整性
        
        Args:
            file_path: 要检查的文件路径
            
        Returns:
            包含try-except结构问题的字典列表
        """
        issues = []
        
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
                # 尝试解析AST，如果有语法错误，会引发异常
                tree = ast.parse(source)
            except SyntaxError as e:
                # 如果是由于try-except结构不完整引起的语法错误
                if "expected 'except' or 'finally'" in str(e):
                    issues.append({
                        'line': e.lineno,
                        'type': 'try_except',
                        'message': '缺少except或finally语句'
                    })
                else:
                    issues.append({
                        'line': e.lineno,
                        'type': 'syntax',
                        'message': f'语法错误: {str(e)}'
                    })
                return issues
            
            # 使用正则表达式查找潜在的try块
            try_pattern = re.compile(r'\btry\s*:')
            except_pattern = re.compile(r'\bexcept\b')
            finally_pattern = re.compile(r'\bfinally\s*:')
            
            lines = source.split('\n')
            for i, line in enumerate(lines):
                if try_pattern.search(line):
                    # 找到try语句，在接下来的几行中查找except或finally
                    found_handler = False
                    for j in range(i + 1, min(i + 20, len(lines))):
                        if except_pattern.search(lines[j]) or finally_pattern.search(lines[j]):
                            found_handler = True
                            break
                    
                    if not found_handler:
                        # 排除常见的误报情况（文件内已有try-except结构的检查函数）
                        if 'check_try_except_structure' not in line and 'fix_try_except' not in line:
                            issues.append({
                                'line': i + 1,
                                'type': 'try_except',
                                'message': '找到try语句，但没有找到对应的except或finally语句'
                            })
        except Exception as e:
            logger.error(f"检查文件 {file_path} 的try-except结构时出错: {str(e)}")
        
        return issues
    
    def check_file(self, file_path: str) -> int:
        """
        检查单个文件的所有语法问题
        
        Args:
            file_path: 要检查的文件路径
            
        Returns:
            发现的问题数量
        """
        rel_path = os.path.relpath(file_path, self.project_path)
        logger.info(f"检查文件: {rel_path}")
        
        # 检查缩进问题
        indent_issues = self.check_indentation(file_path)
        
        # 检查try-except结构
        try_except_issues = self.check_try_except_structure(file_path)
        
        # 合并所有问题
        all_issues = indent_issues + try_except_issues
        
        # 按行号排序
        all_issues.sort(key=lambda x: x['line'])
        
        # 输出问题
        if all_issues:
            logger.warning(f"在文件 {rel_path} 中发现 {len(all_issues)} 个问题:")
            for issue in all_issues:
                logger.warning(f"  第 {issue['line']} 行: {issue['message']}")
        
        return len(all_issues)
    
    def run(self) -> int:
        """
        运行检查器检查所有Python文件
        
        Returns:
            发现的问题总数
        """
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            python_files = self.find_python_files()
            logger.info(f"找到 {len(python_files)} 个Python文件需要检查")
            
            total_issues = 0
            for file_path in python_files:
                issues = self.check_file(file_path)
                total_issues += issues
            
            if total_issues > 0:
                logger.warning(f"共发现 {total_issues} 个语法问题")
            else:
                logger.info("检查完成，未发现语法问题")
            
            return total_issues
        except Exception as e:
            logger.error(f"检查过程中出错: {str(e)}")
            return -1

def main():
    """主函数"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        if len(sys.argv) > 1:
            project_path = sys.argv[1]
        else:
            project_path = os.getcwd()
        
        exclude_dirs = ['venv', 'env', '.venv', '.env', '__pycache__', 'node_modules', 'backups']
        if len(sys.argv) > 2:
            exclude_dirs.extend(sys.argv[2].split(','))
        
        checker = SyntaxChecker(project_path, exclude_dirs)
        return checker.run()
    except Exception as e:
        logger.error(f"执行过程中出错: {str(e)}")
        return -1

if __name__ == "__main__":
    sys.exit(main()) 