#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WSGI入口点
用于生产环境启动Web应用
"""

from app import create_app
import logging

# 创建应用实例
app = create_app()

# 设置日志
logger = logging.getLogger(__name__)

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