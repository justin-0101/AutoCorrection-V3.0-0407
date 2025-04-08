#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
关系管理工具模块
提供统一的模型关系定义工具和辅助函数
"""

import logging
from sqlalchemy.orm import relationship, backref
from typing import Any, Dict, Optional, Type, Union, List, Tuple

logger = logging.getLogger(__name__)

# 默认关系参数
DEFAULT_RELATIONSHIP_PARAMS = {
    'lazy': 'select',  # 默认使用select懒加载策略
    'cascade': 'all, delete-orphan',  # 默认级联所有操作，包括删除孤儿记录
    'passive_deletes': True,  # 允许被动删除
    'enable_typechecks': True,  # 启用类型检查
}

# 默认反向引用参数
DEFAULT_BACKREF_PARAMS = {
    'lazy': 'select',  # 默认使用select懒加载策略
    'cascade': 'all',  # 默认级联所有操作
    'passive_deletes': True,  # 允许被动删除
}

# 懒加载策略映射
LAZY_LOAD_STRATEGIES = {
    'select': '标准懒加载，第一次访问属性时加载',
    'joined': '即时加载，使用JOIN语句加载关联对象',
    'subquery': '即时加载，使用子查询加载关联对象',
    'selectin': '即时集合加载，使用IN操作符批量加载关联对象',
    'raise': '访问未加载的属性时引发异常',
    'noload': '不加载关联对象',
    'immediate': '立即执行加载策略',
    'dynamic': '返回可查询的Query对象而不是加载对象',
}

def standard_relationship(
    target: str,
    backref_name: Optional[str] = None,
    lazy: str = 'select',
    cascade: str = 'all, delete-orphan',
    **kwargs
) -> relationship:
    """
    创建标准化的关系定义
    
    Args:
        target: 目标模型类名或类引用
        backref_name: 反向引用名称，如果为None则不创建反向引用
        lazy: 懒加载策略
        cascade: 级联策略
        **kwargs: 其他关系参数
        
    Returns:
        relationship: SQLAlchemy关系对象
    """
    # 合并默认参数和自定义参数
    params = DEFAULT_RELATIONSHIP_PARAMS.copy()
    params.update({
        'lazy': lazy,
        'cascade': cascade,
    })
    params.update(kwargs)
    
    # 如果提供了反向引用名称，则创建反向引用
    if backref_name:
        backref_params = DEFAULT_BACKREF_PARAMS.copy()
        # 对于多对一关系，反向引用不应包含delete-orphan
        if 'backref_cascade' in kwargs:
            backref_params['cascade'] = kwargs.pop('backref_cascade')
        if 'backref_lazy' in kwargs:
            backref_params['lazy'] = kwargs.pop('backref_lazy')
            
        backref_obj = backref(backref_name, **backref_params)
        params['backref'] = backref_obj
    
    # 记录关系定义
    logger.debug(f"创建关系定义: {target}, 反向引用: {backref_name}, 懒加载策略: {lazy}, 级联策略: {cascade}")
    
    return relationship(target, **params)

def one_to_many(
    target: str,
    backref_name: str,
    lazy: str = 'select',
    **kwargs
) -> relationship:
    """
    创建一对多关系
    
    Args:
        target: 目标模型类名或类引用
        backref_name: 反向引用名称
        lazy: 懒加载策略
        **kwargs: 其他关系参数
        
    Returns:
        relationship: SQLAlchemy关系对象
    """
    return standard_relationship(
        target,
        backref_name=backref_name,
        lazy=lazy,
        cascade='all, delete-orphan',
        backref_cascade='all',  # 一对多关系中，多方不应删除一方
        **kwargs
    )

def many_to_one(
    target: str,
    backref_name: Optional[str] = None,
    lazy: str = 'select',
    **kwargs
) -> relationship:
    """
    创建多对一关系
    
    Args:
        target: 目标模型类名或类引用
        backref_name: 反向引用名称，如果为None则不创建反向引用
        lazy: 懒加载策略
        **kwargs: 其他关系参数
        
    Returns:
        relationship: SQLAlchemy关系对象
    """
    return standard_relationship(
        target,
        backref_name=backref_name,
        lazy=lazy,
        cascade='all',  # 多对一关系中，不应包含delete-orphan
        backref_cascade='all, delete-orphan' if backref_name else None,
        **kwargs
    )

def many_to_many(
    target: str,
    secondary: str,
    backref_name: Optional[str] = None,
    lazy: str = 'select',
    **kwargs
) -> relationship:
    """
    创建多对多关系
    
    Args:
        target: 目标模型类名或类引用
        secondary: 关联表名称
        backref_name: 反向引用名称，如果为None则不创建反向引用
        lazy: 懒加载策略
        **kwargs: 其他关系参数
        
    Returns:
        relationship: SQLAlchemy关系对象
    """
    return standard_relationship(
        target,
        backref_name=backref_name,
        lazy=lazy,
        secondary=secondary,
        cascade='all',  # 多对多关系中，不应包含delete-orphan
        backref_cascade='all',
        **kwargs
    )

def one_to_one(
    target: str,
    backref_name: str,
    lazy: str = 'select',
    **kwargs
) -> relationship:
    """
    创建一对一关系
    
    Args:
        target: 目标模型类名或类引用
        backref_name: 反向引用名称
        lazy: 懒加载策略
        **kwargs: 其他关系参数
        
    Returns:
        relationship: SQLAlchemy关系对象
    """
    kwargs['uselist'] = False
    
    return standard_relationship(
        target,
        backref_name=backref_name,
        lazy=lazy,
        cascade='all, delete-orphan',
        backref_cascade='all',
        **kwargs
    )

def check_relationships(model_class: Type) -> List[Dict[str, Any]]:
    """
    检查模型的关系定义，找出潜在问题
    
    Args:
        model_class: 模型类
        
    Returns:
        List[Dict[str, Any]]: 关系问题列表
    """
    issues = []
    
    # 获取模型的所有关系
    for rel_name, rel in model_class.__mapper__.relationships.items():
        # 检查级联参数
        if 'all' not in rel.cascade and 'save-update' not in rel.cascade:
            issues.append({
                'type': 'cascade',
                'relation': rel_name,
                'current': rel.cascade,
                'recommended': 'all' if rel.collection else 'all, delete-orphan',
                'message': f"缺少必要的级联参数，建议使用 'all' 或 'all, delete-orphan'"
            })
        
        # 检查懒加载策略
        if rel.lazy not in LAZY_LOAD_STRATEGIES:
            issues.append({
                'type': 'lazy',
                'relation': rel_name,
                'current': rel.lazy,
                'recommended': 'select',
                'message': f"使用了未知的懒加载策略: {rel.lazy}"
            })
        
        # 检查反向引用
        if not rel.backref and not rel.back_populates:
            issues.append({
                'type': 'backref',
                'relation': rel_name,
                'current': None,
                'recommended': f"{model_class.__tablename__}",
                'message': f"关系没有定义反向引用，建议添加backref或back_populates"
            })
    
    return issues

def fix_relationship(
    model_class: Type,
    rel_name: str,
    **kwargs
) -> bool:
    """
    修复模型的关系定义
    
    Args:
        model_class: 模型类
        rel_name: 关系名称
        **kwargs: 要更新的关系参数
        
    Returns:
        bool: 是否成功修复
    """
    # 这个函数需要在运行时修改模型定义，较为复杂
    # 实际应用中，通常建议修改模型代码而不是运行时修改
    logger.warning(f"修复关系定义需要修改代码，请手动更新 {model_class.__name__}.{rel_name}")
    
    # 返回修复建议
    rel = model_class.__mapper__.relationships.get(rel_name)
    if not rel:
        logger.error(f"关系 {rel_name} 不存在于 {model_class.__name__}")
        return False
    
    target = rel.argument
    if callable(target):
        target = target()
    
    suggestions = []
    
    if 'cascade' in kwargs:
        suggestions.append(f"cascade='{kwargs['cascade']}'")
    
    if 'lazy' in kwargs:
        suggestions.append(f"lazy='{kwargs['lazy']}'")
    
    if 'backref' in kwargs:
        suggestions.append(f"backref='{kwargs['backref']}'")
    
    if suggestions:
        logger.info(f"建议修改 {model_class.__name__}.{rel_name} 关系定义为: {', '.join(suggestions)}")
    
    return True

def analyze_model_relationships(model_class: Type) -> Dict[str, Any]:
    """
    分析模型的关系定义
    
    Args:
        model_class: 模型类
        
    Returns:
        Dict[str, Any]: 关系分析结果
    """
    result = {
        'model': model_class.__name__,
        'table': model_class.__tablename__,
        'relationships': [],
        'issues': check_relationships(model_class),
    }
    
    for rel_name, rel in model_class.__mapper__.relationships.items():
        target = rel.argument
        if callable(target):
            target = target()
            
        rel_info = {
            'name': rel_name,
            'target': target.__name__ if hasattr(target, '__name__') else str(target),
            'type': 'one_to_many' if rel.collection else 'many_to_one',
            'uselist': rel.uselist,
            'lazy': rel.lazy,
            'cascade': rel.cascade,
            'backref': rel.backref.key if rel.backref else None,
            'back_populates': rel.back_populates,
        }
        
        # 确定关系类型
        if rel.secondary is not None:
            rel_info['type'] = 'many_to_many'
            rel_info['secondary'] = rel.secondary.name
        elif rel.uselist is False and rel.backref and rel.backref.kwargs.get('uselist') is False:
            rel_info['type'] = 'one_to_one'
            
        result['relationships'].append(rel_info)
    
    return result 