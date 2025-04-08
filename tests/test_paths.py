#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试路径设置
在运行测试前设置Python路径
"""

import os
import sys
import os.path

# 获取项目根目录的绝对路径
current_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = current_dir

# 将项目根目录添加到Python路径中
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
    print(f"已将 {root_dir} 添加到Python路径")

print("Python路径设置完成，现在可以正常导入应用程序模块")

# 检查是否可以导入应用程序模块
try:
    import app
    print("成功导入app模块")
except ImportError as e:
    print(f"导入app模块失败: {e}")

try:
    from app.core.services.container import ServiceContainer
    print("成功导入ServiceContainer类")
except ImportError as e:
    print(f"导入ServiceContainer类失败: {e}")

# 如果是作为脚本运行，则显示Python路径
if __name__ == "__main__":
    print("\nPython路径:")
    for path in sys.path:
        print(f" - {path}") 