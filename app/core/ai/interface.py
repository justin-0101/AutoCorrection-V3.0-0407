#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI客户端接口模块
定义AI服务的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class IAIClient(ABC):
    """AI客户端接口"""
    
    @abstractmethod
    def correct_essay(self, content: str) -> Dict[str, Any]:
        """
        批改作文
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 批改结果
        """
        pass
    
    @abstractmethod
    def analyze_text(self, content: str) -> Dict[str, Any]:
        """
        分析文本
        
        Args:
            content: 文本内容
            
        Returns:
            Dict: 分析结果
        """
        pass
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            str: 生成的文本
        """
        pass 