#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文数据验证模块
"""

import logging
from app.errors import ValidationError
from app.models.essay import EssaySourceType

logger = logging.getLogger(__name__)

class EssayValidator:
    """作文数据验证器"""
    
    @staticmethod
    def validate_essay_data(title, content, source_type=None, grade=None, author_name=None):
        """
        验证作文数据
        
        Args:
            title: 作文标题
            content: 作文内容
            source_type: 来源类型
            grade: 年级水平
            author_name: 作者姓名
            
        Raises:
            ValidationError: 当验证失败时抛出
        """
        errors = []
        
        # 验证标题
        if not title:
            errors.append("标题不能为空")
        elif len(title) > 200:
            errors.append("标题长度不能超过200个字符")
            
        # 验证内容
        if not content:
            errors.append("内容不能为空")
        elif len(content) < 50:
            errors.append("内容长度不能少于50个字符")
        elif len(content) > 10000:
            errors.append("内容长度不能超过10000个字符")
            
        # 验证来源类型
        if source_type and source_type not in [t.value for t in EssaySourceType]:
            errors.append(f"无效的来源类型: {source_type}")
            
        # 验证年级
        if grade and not isinstance(grade, str):
            errors.append("年级必须是字符串类型")
        elif grade and len(grade) > 50:
            errors.append("年级长度不能超过50个字符")
            
        # 验证作者姓名
        if author_name and not isinstance(author_name, str):
            errors.append("作者姓名必须是字符串类型")
        elif author_name and len(author_name) > 100:
            errors.append("作者姓名长度不能超过100个字符")
            
        # 如果有错误，抛出异常
        if errors:
            raise ValidationError("\n".join(errors))
            
        return True 