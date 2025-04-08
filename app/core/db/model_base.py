#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型基类模块
提供所有模型的基类、通用方法和标准字段
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr

logger = logging.getLogger(__name__)

class ModelBase:
    """
    模型基类，提供共享的基础属性和方法
    所有模型都应该继承这个类
    """
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 时间戳字段
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 软删除标记
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # 声明表命名约定
    @declared_attr
    def __tablename__(cls) -> str:
        """根据类名生成表名"""
        import re
        # 将驼峰命名转换为下划线命名
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def to_dict(self, exclude: List[str] = None) -> Dict[str, Any]:
        """
        将模型对象转换为字典
        
        Args:
            exclude: 要排除的字段列表
            
        Returns:
            Dict[str, Any]: 模型对象的字典表示
        """
        exclude = exclude or []
        result = {}
        
        for key in self.__mapper__.c.keys():
            if key in exclude:
                continue
            value = getattr(self, key)
            
            # 处理日期时间类型
            if isinstance(value, datetime):
                value = value.isoformat()
                
            result[key] = value
        
        return result
    
    def update(self, **kwargs) -> bool:
        """
        批量更新模型属性
        
        Args:
            **kwargs: 要更新的字段和值
            
        Returns:
            bool: 是否有字段被更新
        """
        updated = False
        
        # 首先验证字段值
        validation_errors = self.validate_fields_dict(kwargs)
        if validation_errors:
            error_fields = ", ".join(validation_errors.keys())
            logger.warning(f"更新模型 {self.__class__.__name__} 时存在验证错误: {error_fields}")
            raise ValueError(f"字段验证失败: {validation_errors}")
        
        # 遍历字段并更新
        for key, value in kwargs.items():
            if hasattr(self, key) and getattr(self, key) != value:
                setattr(self, key, value)
                updated = True
        
        return updated
    
    def validate_fields_dict(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        验证字段值字典
        
        Args:
            data: 字段名到值的映射
            
        Returns:
            Dict[str, List[str]]: 字段错误信息
        """
        from app.core.db.model_validator import validate_field
        
        errors = {}
        for field_name, value in data.items():
            if hasattr(self, field_name):
                field_errors = validate_field(self, field_name, value)
                if field_errors:
                    errors[field_name] = field_errors
        
        return errors
    
    def validate(self) -> Dict[str, List[str]]:
        """
        验证所有字段
        
        Returns:
            Dict[str, List[str]]: 字段错误信息
        """
        from app.core.db.model_validator import validate_model
        return validate_model(self)
    
    def save(self, commit: bool = True) -> bool:
        """
        保存模型对象到数据库
        
        Args:
            commit: 是否立即提交
            
        Returns:
            bool: 是否成功保存
        """
        from app.core.db import get_session
        session = get_session()
        
        try:
            # 首先验证字段
            errors = self.validate()
            if errors:
                error_fields = ", ".join(errors.keys())
                logger.warning(f"保存模型 {self.__class__.__name__} 时存在验证错误: {error_fields}")
                raise ValueError(f"字段验证失败: {errors}")
            
            # 添加到会话并提交
            session.add(self)
            if commit:
                session.commit()
            
            return True
        except Exception as e:
            if commit:
                session.rollback()
            logger.error(f"保存模型 {self.__class__.__name__} 时出错: {str(e)}")
            raise
    
    def delete(self, hard: bool = False, commit: bool = True) -> bool:
        """
        删除模型对象
        
        Args:
            hard: 是否硬删除
            commit: 是否立即提交
            
        Returns:
            bool: 是否成功删除
        """
        from app.core.db import get_session
        session = get_session()
        
        try:
            if hard:
                # 硬删除
                session.delete(self)
            else:
                # 软删除
                self.is_deleted = True
                session.add(self)
            
            if commit:
                session.commit()
            
            return True
        except Exception as e:
            if commit:
                session.rollback()
            logger.error(f"删除模型 {self.__class__.__name__} 时出错: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional['ModelBase']:
        """
        通过ID获取对象
        
        Args:
            id: 对象ID
            
        Returns:
            Optional[ModelBase]: 找到的对象，如果不存在则返回None
        """
        from app.core.db import get_session
        session = get_session()
        
        return session.query(cls).filter(cls.id == id, cls.is_deleted == False).first()
    
    @classmethod
    def get_all(cls, include_deleted: bool = False) -> List['ModelBase']:
        """
        获取所有对象
        
        Args:
            include_deleted: 是否包含已删除的对象
            
        Returns:
            List[ModelBase]: 对象列表
        """
        from app.core.db import get_session
        session = get_session()
        
        query = session.query(cls)
        if not include_deleted:
            query = query.filter(cls.is_deleted == False)
        
        return query.all()
    
    @classmethod
    def count(cls, include_deleted: bool = False) -> int:
        """
        获取对象总数
        
        Args:
            include_deleted: 是否包含已删除的对象
            
        Returns:
            int: 对象总数
        """
        from app.core.db import get_session
        session = get_session()
        
        query = session.query(cls)
        if not include_deleted:
            query = query.filter(cls.is_deleted == False)
        
        return query.count()
    
    def __repr__(self) -> str:
        """模型对象的字符串表示"""
        return f"<{self.__class__.__name__} {self.id}>"
    
    @classmethod
    def define_relationship(cls, rel_type: str, target: str, **kwargs) -> None:
        """
        定义模型关系
        
        Args:
            rel_type: 关系类型，one_to_many、many_to_one、many_to_many、one_to_one
            target: 目标模型类名或类引用
            **kwargs: 关系参数
        """
        from app.core.db.relationship_manager import one_to_many, many_to_one, many_to_many, one_to_one
        
        # 获取关系函数
        rel_funcs = {
            'one_to_many': one_to_many,
            'many_to_one': many_to_one,
            'many_to_many': many_to_many,
            'one_to_one': one_to_one
        }
        
        rel_func = rel_funcs.get(rel_type)
        if not rel_func:
            raise ValueError(f"未知的关系类型: {rel_type}")
        
        # 创建关系
        rel = rel_func(target, **kwargs)
        
        # 获取关系名称
        rel_name = kwargs.get('name')
        if not rel_name:
            raise ValueError("必须提供关系名称")
        
        # 将关系添加到模型类
        setattr(cls, rel_name, rel)
    
    @classmethod
    def set_validators(cls, field_name: str, *validators) -> None:
        """
        设置字段验证器
        
        Args:
            field_name: 字段名
            *validators: 验证器函数
        """
        from app.core.db.model_validator import set_validators, create_validators
        set_validators(cls, field_name, create_validators(*validators)) 