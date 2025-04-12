#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批改服务接口定义模块
用于定义服务间的接口契约，避免循环导入
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import datetime

class ICorrectionService(ABC):
    """批改服务接口定义"""
    
    @abstractmethod
    def perform_correction(self, essay_id: int) -> Dict[str, Any]:
        """
        执行作文批改
        
        Args:
            essay_id: 作文ID
            
        Returns:
            Dict: 批改结果
        """
        pass
    
    @abstractmethod
    def get_correction_result(self, essay_id: int) -> Dict[str, Any]:
        """
        获取批改结果
        
        Args:
            essay_id: 作文ID
            
        Returns:
            Dict: 批改结果
        """
        pass
    
    @abstractmethod
    def submit_essay(self, user_id: int, title: str, content: str, grade: str = 'junior') -> Dict[str, Any]:
        """
        提交作文进行批改
        
        Args:
            user_id: 用户ID
            title: 作文标题
            content: 作文内容
            grade: 年级水平
            
        Returns:
            Dict: 提交结果
        """
        pass
    
    @abstractmethod
    def get_essay(self, essay_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取作文信息
        
        Args:
            essay_id: 作文ID
            user_id: 用户ID（可选，用于权限检查）
            
        Returns:
            Dict: 作文信息
        """
        pass
    
    @abstractmethod
    def get_user_essays(self, user_id: int, page: int = 1, per_page: int = 10, 
                        status: Optional[str] = None) -> Dict[str, Any]:
        """
        获取用户的作文列表
        
        Args:
            user_id: 用户ID
            page: 页码
            per_page: 每页数量
            status: 作文状态过滤
            
        Returns:
            Dict: 作文列表
        """
        pass
    
class CorrectionResult:
    """批改结果数据传输对象"""
    
    def __init__(self, essay_id: int, status: str, score: Optional[float] = None, 
                 content: Optional[Dict[str, Any]] = None):
        self.essay_id = essay_id
        self.status = status
        self.score = score
        self.content = content or {}
        self.timestamp = datetime.datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            'essay_id': self.essay_id,
            'status': self.status,
            'score': self.score,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrectionResult':
        """从字典创建实例"""
        result = cls(
            essay_id=data.get('essay_id'),
            status=data.get('status'),
            score=data.get('score'),
            content=data.get('content')
        )
        if 'timestamp' in data:
            try:
                result.timestamp = datetime.datetime.fromisoformat(data['timestamp'])
            except (ValueError, TypeError):
                pass
        return result
    
    def get_feedback(self) -> Dict[str, Any]:
        """获取反馈内容"""
        return {
            'score': self.score,
            'feedback': self.content.get('feedback', ''),
            'suggestions': self.content.get('suggestions', []),
            'errors': self.content.get('errors', [])
        } 