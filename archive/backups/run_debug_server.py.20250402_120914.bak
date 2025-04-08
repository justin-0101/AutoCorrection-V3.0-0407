#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
以调试模式启动服务器，显示所有日志信息
"""

import os
import sys
import subprocess

# 设置环境变量以启用详细日志
os.environ['DEBUG'] = 'True'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['DISABLE_SSL_VERIFY'] = 'true'

print("正在以调试模式启动服务器...")
print("设置环境变量: DEBUG=True, LOG_LEVEL=DEBUG")

# 启动服务器
cmd = [sys.executable, "final_combined_server.py"]
subprocess.run(cmd) 