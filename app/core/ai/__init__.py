#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI客户端模块
提供各种AI API的客户端
"""

import os
import logging
from typing import Dict, Any, Optional

from app.core.ai.api_client import BaseAPIClient
from app.core.ai.open_ai_client import OpenAIClient
from app.core.ai.deepseek_client import DeepseekClient
from app.core.ai.aliyun_qianwen_client import AliyunQianwenClient

# 配置日志
logger = logging.getLogger(__name__)

class AIClientFactory:
    """
    AI客户端工厂
    用于创建各种AI客户端实例
    """
    
    # 单例模式
    _instance = None
    
    # 客户端缓存
    _clients = {}
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(AIClientFactory, cls).__new__(cls)
            cls._instance._clients = {}
            
            # 自动注册到服务容器
            try:
                from app.core.services.container import container, ServiceScope
                if not container.has('ai_client_factory'):
                    container.register('ai_client_factory', cls._instance, ServiceScope.SINGLETON)
                    logger.info("AI客户端工厂已自动注册到服务容器")
            except Exception as e:
                logger.error(f"注册AI客户端工厂到服务容器失败: {str(e)}")
                
        return cls._instance
    
    def get_client(self, provider_name: Optional[str] = None) -> Any:
        """
        获取指定提供商的客户端实例
        
        Args:
            provider_name: 提供商名称，如果为None则从环境变量获取
            
        Returns:
            Any: 客户端实例
            
        Raises:
            ConfigurationError: 当无法确定AI提供商时
        """
        # 尝试从多个来源获取提供商名称
        provider = provider_name or os.environ.get('AI_PROVIDER') or os.environ.get('DEFAULT_AI_PROVIDER')
        
        if not provider:
            # 如果环境变量中未配置，使用默认值并记录警告
            logger.warning("AI provider未配置，使用默认值'deepseek'")
            provider = 'deepseek'
            
        # 检查缓存中是否已有该客户端
        if provider in self._clients:
            logger.debug(f"从缓存获取AI客户端: {provider}")
            return self._clients[provider]
        
        # 创建新客户端
        client = None
        
        if provider == "openai":
            client = OpenAIClient()
        elif provider == "deepseek":
            client = DeepseekClient()
        elif provider == "aliyun_qianwen":
            client = AliyunQianwenClient()
        else:
            logger.warning(f"未知的AI提供商: {provider}，使用默认提供商(deepseek)")
            client = DeepseekClient()
        
        # 缓存客户端
        if client:
            self._clients[provider] = client
            logger.info(f"创建并缓存AI客户端: {provider}")
        
        return client
    
    def clear_cache(self):
        """清除客户端缓存"""
        self._clients.clear()
        logger.debug("已清除AI客户端缓存")

# 创建全局工厂实例
ai_client_factory = AIClientFactory()

def get_ai_client(provider_name: str) -> Any:
    """
    获取AI客户端的便捷函数
    
    Args:
        provider_name: 提供商名称
        
    Returns:
        Any: 客户端实例
    """
    return ai_client_factory.get_client(provider_name) 