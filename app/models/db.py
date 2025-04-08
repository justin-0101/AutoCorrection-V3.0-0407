#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库连接和基础模型配置
"""

import logging
from datetime import datetime
from app.extensions import db
from app.core.db.model_base import ModelBase
from app.core.db.field_naming import get_standard_fields, get_field_naming_suggestions
from app.core.db.model_utils import standardize_datetime, standardize_boolean

logger = logging.getLogger(__name__)

# 创建基础模型类
class BaseModel(db.Model, ModelBase):
    """基础模型类，所有模型都应该继承这个类"""
    __abstract__ = True 

    # 已经从ModelBase继承了通用字段和方法:
    # - id: 主键
    # - created_at: 创建时间
    # - updated_at: 更新时间
    # - is_deleted: 软删除标记
    # - to_dict(): 转为字典方法
    # - update(): 批量更新方法
    # - get_by_id(): 通过ID获取对象
    # - get_all(): 获取所有对象
    # - save(): 保存对象
    # - delete(): 删除对象
    
    # 保持与现有代码的兼容性
    def soft_delete(self):
        """软删除（兼容旧代码，推荐使用delete方法）"""
        return self.delete(hard=False)

    @classmethod
    def check_field_naming(cls):
        """
        检查字段命名是否符合规范
        
        Returns:
            List[Dict[str, str]]: 字段命名建议列表
        """
        from app.core.db.field_naming import get_field_naming_suggestions
        return get_field_naming_suggestions(cls)
        
    def validate_fields(self):
        """
        验证字段值是否符合规范
        
        Returns:
            Dict[str, List[str]]: 包含字段名和错误消息的字典
        """
        from app.core.db.model_utils import validate_model
        return validate_model(self)
        
    @classmethod
    def apply_standard_fields(cls, **kwargs):
        """
        创建模型实例并应用标准字段处理
        
        Args:
            **kwargs: 字段值
            
        Returns:
            BaseModel: 创建的模型实例
        """
        # 标准化日期时间字段
        for field in ['created_at', 'updated_at']:
            if field in kwargs:
                kwargs[field] = standardize_datetime(kwargs[field])
                
        # 标准化布尔字段
        for field in ['is_deleted', 'is_active', 'is_default', 'is_public']:
            if field in kwargs:
                kwargs[field] = standardize_boolean(kwargs[field])
        
        # 创建实例
        instance = cls(**kwargs)
        
        # 验证字段
        errors = instance.validate_fields()
        if errors:
            logger.warning(f"模型 {cls.__name__} 字段验证错误: {errors}")
            
        return instance 