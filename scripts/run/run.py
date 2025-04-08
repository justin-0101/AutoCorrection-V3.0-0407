#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
应用启动入口脚本
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# 确保工作目录正确设置
root_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(root_dir)

# 设置日志格式
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        RotatingFileHandler('logs/app.log', maxBytes=10 * 1024 * 1024, backupCount=5),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger(__name__)

# 导入和创建应用，提供给Celery任务和其他模块使用
from app import create_app
app = create_app()

def main():
    """启动Flask应用"""
    try:
        # 首先应用猴子补丁，修复潜在的属性错误
        from app.patch import apply_patches
        apply_patches()
        
        # 已在文件顶层创建了应用实例
        
        # 获取命令行参数
        debug = "--debug" in sys.argv
        port = 5000
        for i, arg in enumerate(sys.argv):
            if arg == '--port' and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    pass
                
        # 输出路由信息
        print("应用路由:")
        for rule in app.url_map.iter_rules():
            methods = ','.join(sorted(rule.methods))
            print(f"{rule.endpoint}: {rule.rule} [{methods}]")
        
        # 启动应用
        host = '0.0.0.0'
        print(f"正在启动Flask应用，主机: {host}, 端口: {port}, 调试模式: {debug}")
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main() 