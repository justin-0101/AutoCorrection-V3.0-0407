#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WSGI入口点
用于生产环境启动Web应用
"""

# 在导入任何其他模块之前应用eventlet猴子补丁
import os
import eventlet
eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)
os.environ['EVENTLET_PATCHED'] = 'true'
print("eventlet猴子补丁已提前应用")

from app import create_app
import logging

# 创建应用实例
app = create_app()

# 设置日志
# 获取 Flask 应用的 logger
logger = app.logger 
# 设置日志级别为 INFO，以便看到 logger.info 的输出
logger.setLevel(logging.INFO)
# 可以选择添加一个 StreamHandler 将日志输出到控制台（虽然 Flask 默认可能已经做了）
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("应用日志已配置，级别设置为 INFO")

# 初始化容器
try:
    from app.core.services.service_registry_di import ServiceContainer
    ServiceContainer.init_app(app)
    logger.info("依赖注入容器已初始化")
except Exception as e:
    logger.warning(f"依赖注入容器初始化失败: {str(e)}")

if __name__ == '__main__':
    # 开发模式下直接运行
    app.run(host='0.0.0.0', port=5000, debug=True) 