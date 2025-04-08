#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型迁移工具模块
提供检测和修正现有模型字段命名的工具
"""

import logging
import inspect
from typing import Dict, List, Set, Type, Any
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.ext.declarative import DeclarativeMeta

from app.core.db.field_naming import (
    get_standard_fields, 
    check_field_naming, 
    get_field_naming_suggestions,
    FIELD_NAME_MAPPING
)
from app.core.db.transaction import atomic_operation

logger = logging.getLogger(__name__)

def scan_models(package_name: str = 'app.models') -> List[Type]:
    """
    扫描指定包中的所有模型类
    
    Args:
        package_name: 包名
        
    Returns:
        List[Type]: 模型类列表
    """
    import importlib
    import pkgutil
    import sys
    
    models = []
    
    try:
        # 导入包
        package = importlib.import_module(package_name)
        
        # 扫描包中的所有模块
        for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
            if is_pkg:
                # 如果是子包，递归扫描
                models.extend(scan_models(name))
            else:
                try:
                    # 导入模块
                    module = importlib.import_module(name)
                    
                    # 查找所有模型类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            inspect.isclass(attr) and 
                            isinstance(attr, DeclarativeMeta) and
                            attr.__module__ == module.__name__ and
                            not attr.__name__.startswith('_') and
                            hasattr(attr, '__tablename__')
                        ):
                            models.append(attr)
                except Exception as e:
                    logger.error(f"扫描模块 {name} 时出错: {str(e)}")
                    continue
    except Exception as e:
        logger.error(f"扫描包 {package_name} 时出错: {str(e)}")
    
    return models

def get_model_field_issues(model_class: Type) -> Dict[str, str]:
    """
    获取模型字段命名问题
    
    Args:
        model_class: 模型类
        
    Returns:
        Dict[str, str]: 字段名到问题描述的映射
    """
    issues = {}
    
    for column in sqlalchemy_inspect(model_class).columns:
        field_name = column.name
        field_type = column.type.__class__.__name__
        
        is_valid, message = check_field_naming(field_name, field_type)
        if not is_valid:
            issues[field_name] = message
    
    return issues

def get_model_field_renames(model_class: Type) -> Dict[str, str]:
    """
    获取模型字段重命名建议
    
    Args:
        model_class: 模型类
        
    Returns:
        Dict[str, str]: 旧字段名到新字段名的映射
    """
    renames = {}
    
    for column in sqlalchemy_inspect(model_class).columns:
        field_name = column.name
        
        if field_name in FIELD_NAME_MAPPING:
            renames[field_name] = FIELD_NAME_MAPPING[field_name]
    
    return renames

def generate_migration_script(model_class: Type) -> str:
    """
    生成模型迁移脚本
    
    Args:
        model_class: 模型类
        
    Returns:
        str: 迁移脚本
    """
    renames = get_model_field_renames(model_class)
    if not renames:
        return f"# 模型 {model_class.__name__} 无需重命名字段"
    
    script_lines = [
        f"# 模型 {model_class.__name__} 字段重命名",
        "from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey",
        "from alembic import op",
        "import sqlalchemy as sa",
        "",
        "def upgrade():",
    ]
    
    for old_name, new_name in renames.items():
        script_lines.append(f"    # 将 {old_name} 重命名为 {new_name}")
        script_lines.append(f"    op.alter_column('{model_class.__tablename__}', '{old_name}', new_column_name='{new_name}')")
    
    script_lines.extend([
        "",
        "def downgrade():",
    ])
    
    for old_name, new_name in renames.items():
        script_lines.append(f"    # 将 {new_name} 重命名回 {old_name}")
        script_lines.append(f"    op.alter_column('{model_class.__tablename__}', '{new_name}', new_column_name='{old_name}')")
    
    return "\n".join(script_lines)

def check_all_models() -> Dict[str, Dict[str, Any]]:
    """
    检查所有模型的字段命名
    
    Returns:
        Dict[str, Dict[str, Any]]: 模型名到问题的映射
    """
    result = {}
    
    # 扫描所有模型
    models = scan_models()
    
    for model in models:
        issues = get_model_field_issues(model)
        if issues:
            result[model.__name__] = {
                'issues': issues,
                'renames': get_model_field_renames(model),
                'model': model
            }
    
    return result

def generate_migration_plan() -> str:
    """
    生成迁移计划
    
    Returns:
        str: 迁移计划文本
    """
    all_issues = check_all_models()
    
    if not all_issues:
        return "所有模型字段命名符合规范，无需迁移"
    
    lines = ["# 模型字段命名迁移计划", ""]
    
    for model_name, info in all_issues.items():
        lines.append(f"## 模型: {model_name}")
        lines.append("")
        
        # 添加问题描述
        lines.append("### 发现的问题:")
        for field, issue in info['issues'].items():
            lines.append(f"- {field}: {issue}")
        lines.append("")
        
        # 添加重命名建议
        if info['renames']:
            lines.append("### 重命名建议:")
            for old, new in info['renames'].items():
                lines.append(f"- {old} -> {new}")
            lines.append("")
        
        # 添加迁移脚本
        lines.append("### 迁移脚本:")
        lines.append("```python")
        lines.append(generate_migration_script(info['model']))
        lines.append("```")
        lines.append("")
    
    return "\n".join(lines)

def apply_field_renames(model_class: Type, dry_run: bool = True) -> Dict[str, str]:
    """
    应用字段重命名
    
    Args:
        model_class: 模型类
        dry_run: 是否只是模拟执行
        
    Returns:
        Dict[str, str]: 应用的重命名
    """
    renames = get_model_field_renames(model_class)
    applied = {}
    
    if not renames:
        return applied
    
    logger.info(f"模型 {model_class.__name__} 需要重命名以下字段: {renames}")
    
    if not dry_run:
        with atomic_operation(f"重命名 {model_class.__name__} 字段") as session:
            for old_name, new_name in renames.items():
                logger.info(f"将 {model_class.__name__}.{old_name} 重命名为 {new_name}")
                # 执行数据库迁移
                session.execute(
                    f"ALTER TABLE {model_class.__tablename__} "
                    f"RENAME COLUMN {old_name} TO {new_name}"
                )
                applied[old_name] = new_name
    else:
        logger.info("仅模拟执行，未实际修改数据库")
        applied = renames
    
    return applied 