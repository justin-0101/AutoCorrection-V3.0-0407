#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改系统入口文件
"""

import os
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# 加载环境变量
load_dotenv()

# 从app包中导入创建的应用
from app import create_app
# 不再从这里导入socketio
# from app.utils.websocket_manager import socketio

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    # 开发模式启动
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # 使用Flask原生方法启动应用，而不是socketio
    print(f"应用程序启动在 http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 