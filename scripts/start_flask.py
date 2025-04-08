#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
启动Flask应用
简化的脚本，仅负责启动Flask应用
"""

import os
import sys
from pathlib import Path

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent.parent
os.chdir(ROOT_DIR)

print("正在启动Flask应用...")
try:
    # 导入创建应用函数
    from app import create_app
    app = create_app()
    
    # 获取端口
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    
    # 输出路由信息
    print("应用路由:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods))
        print(f"{rule.endpoint}: {rule.rule} [{methods}]")
    
    # 启动应用
    print(f"Flask应用正在运行，请访问：http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
    
except Exception as e:
    print(f"启动失败: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 