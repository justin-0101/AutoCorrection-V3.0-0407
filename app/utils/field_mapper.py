#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""字段映射工具，用于处理AI响应中的动态字段名"""

import os
import yaml
import logging
import copy
from typing import Dict, Any, List, Optional, Union

# 配置日志
logger = logging.getLogger(__name__)

class FieldMapper:
    """
    字段映射器，用于标准化不同AI服务的响应字段。
    
    该类负责将不同AI服务提供商的字段名称转换为标准化的内部字段名称，
    确保无论使用哪个AI服务，系统内部处理的数据结构都是一致的。
    
    示例:
        field_mapper = FieldMapper()
        normalized_result = field_mapper.normalize_result(api_response, "deepseek")
    """

    def __init__(self, mapping_file: str = "config/field_mappings.yaml"):
        """
        初始化字段映射器
        
        Args:
            mapping_file: 字段映射配置文件路径
        """
        self.mapping_file = mapping_file
        self.mappings = {}
        self.core_fields = {
            "scores": {
                "total": 0,
                "dimensions": {}
            },
            "analyses": {
                "summary": "",
                "content": "",
                "language": "",
                "structure": ""
            },
            "feedback": {
                "strengths": [],
                "weaknesses": [],
                "improvements": []
            },
            "metadata": {
                "provider": "",
                "model": "",
                "processing_time": 0
            }
        }
        self._load_mappings()
        
    def _load_mappings(self) -> None:
        """从配置文件加载字段映射"""
        try:
            if not os.path.exists(self.mapping_file):
                logger.warning(f"映射文件 {self.mapping_file} 不存在，使用默认映射")
                # 设置默认映射
                self.mappings = {
                    "deepseek": {
                        "scores": {
                            "总得分": "total",
                            "分项得分.内容主旨": "dimensions.content",
                            "分项得分.语言文采": "dimensions.language",
                            "分项得分.文章结构": "dimensions.structure",
                            "分项得分.文面书写": "dimensions.grammar"
                        },
                        "analyses": {
                            "总体评价": "summary",
                            "内容分析": "content",
                            "语言分析": "language",
                            "结构分析": "structure"
                        },
                        "feedback": {
                            "优点": "strengths",
                            "缺点": "weaknesses",
                            "写作建议": "improvements"
                        }
                    }
                }
                return

            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                self.mappings = yaml.safe_load(f) or {}
                
            if not self.mappings:
                logger.warning(f"映射文件 {self.mapping_file} 为空或格式错误")
        except Exception as e:
            logger.exception(f"加载字段映射时出错: {str(e)}")
            self.mappings = {}
            
    def get_standard_field(self, provider: str, category: str, field: str) -> Optional[str]:
        """
        获取标准字段名
        
        Args:
            provider: 服务提供商
            category: 字段类别
            field: 原始字段名
            
        Returns:
            Optional[str]: 标准字段名，如果未找到映射则返回None
        """
        if provider not in self.mappings:
            return None
            
        if category not in self.mappings[provider]:
            return None
            
        return self.mappings[provider][category].get(field)
        
    def normalize_result(self, api_response: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        将API响应标准化为内部格式
        
        Args:
            api_response: API响应数据
            provider: 服务提供商
            
        Returns:
            Dict[str, Any]: 标准化后的结果
        """
        if not api_response or not isinstance(api_response, dict):
            logger.error(f"无效的API响应: {type(api_response)}")
            return self._get_default_structure()
            
        if provider not in self.mappings:
            logger.warning(f"未找到提供商 '{provider}' 的映射")
            return self._get_default_structure()
            
        # 创建结果结构的深拷贝
        result = self._get_default_structure()
        result["metadata"]["provider"] = provider
        
        # 遍历每个类别的映射
        for category, field_mappings in self.mappings[provider].items():
            self._map_category_fields(api_response, result, category, field_mappings)
            
        # 确保核心字段存在
        self._ensure_core_fields(result)
            
        return result
    
    def _map_category_fields(self, source: Dict[str, Any], target: Dict[str, Any], 
                            category: str, field_mappings: Dict[str, str]) -> None:
        """
        映射特定类别的字段
        
        Args:
            source: 源数据
            target: 目标数据
            category: 字段类别
            field_mappings: 字段映射
        """
        for source_field, target_field in field_mappings.items():
            # 处理嵌套字段，如 "分项得分.内容主旨"
            source_value = self._get_nested_value(source, source_field)
            if source_value is None:
                continue
                
            # 验证值类型
            validated_value = self._validate_value(source_value, category, target_field)
            if validated_value is None:
                continue
                
            # 设置目标字段值
            self._set_nested_value(target, category, target_field, validated_value)
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        获取嵌套字段的值
        
        Args:
            data: 数据字典
            field_path: 字段路径，如 "分项得分.内容主旨"
            
        Returns:
            Any: 字段值，如果未找到则返回None
        """
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
            
        return current
        
    def _set_nested_value(self, data: Dict[str, Any], category: str, field_path: str, value: Any) -> None:
        """
        设置嵌套字段的值
        
        Args:
            data: 数据字典
            category: 字段类别
            field_path: 字段路径，如 "dimensions.content"
            value: 要设置的值
        """
        if category not in data:
            logger.warning(f"目标类别 '{category}' 不存在")
            return
            
        target = data[category]
        parts = field_path.split('.')
        
        # 处理嵌套路径
        for i, part in enumerate(parts[:-1]):
            if part not in target:
                target[part] = {}
            elif not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
            
        # 设置最终值
        target[parts[-1]] = value
    
    def _validate_value(self, value: Any, category: str, field: str) -> Any:
        """
        验证字段值的类型
        
        Args:
            value: 要验证的值
            category: 字段类别
            field: 字段名
            
        Returns:
            Any: 验证后的值，如果无效则返回None
        """
        try:
            # 验证分数字段
            if category == "scores":
                if field == "total" or field.startswith("dimensions."):
                    if isinstance(value, (int, float)):
                        return value
                    elif isinstance(value, str) and value.replace('.', '', 1).isdigit():
                        return float(value)
                    else:
                        logger.warning(f"无效的分数值: {value}")
                        return None
                        
            # 验证分析字段
            elif category == "analyses":
                if isinstance(value, str):
                    return value.strip()
                else:
                    return str(value)
                    
            # 验证反馈字段
            elif category == "feedback":
                if field in ["strengths", "weaknesses", "improvements"]:
                    if isinstance(value, list):
                        return [str(item).strip() for item in value if item]
                    elif isinstance(value, str):
                        # 尝试拆分为列表
                        items = [item.strip() for item in value.split('\n') if item.strip()]
                        return items if items else [value.strip()]
                    else:
                        return [str(value)]
                        
            # 元数据字段
            elif category == "metadata":
                if field == "processing_time" and isinstance(value, (int, float)):
                    return value
                else:
                    return str(value)
            
            # 默认情况
            return value
            
        except Exception as e:
            logger.exception(f"验证字段值时出错: {str(e)}")
            return None
    
    def _ensure_core_fields(self, result: Dict[str, Any]) -> None:
        """
        确保核心字段存在
        
        Args:
            result: 结果字典
        """
        # 确保总分在有效范围内
        if "scores" in result and "total" in result["scores"]:
            if not isinstance(result["scores"]["total"], (int, float)):
                result["scores"]["total"] = 0
            else:
                result["scores"]["total"] = max(0, min(50, result["scores"]["total"]))
        
        # 如果有原始数据包含中文字段，则直接使用
        if "_raw_data" in result and isinstance(result["_raw_data"], dict):
            raw_data = result["_raw_data"]
            
            # 如果有总得分，确保转换到标准格式
            if "总得分" in raw_data:
                try:
                    score = float(raw_data["总得分"])
                    if "scores" not in result:
                        result["scores"] = {}
                    result["scores"]["total"] = max(0, min(50, score))
                    
                    # 为向后兼容添加total_score
                    result["total_score"] = result["scores"]["total"]
                except (ValueError, TypeError):
                    pass
            
            # 处理分项得分
            if "分项得分" in raw_data and isinstance(raw_data["分项得分"], dict):
                if "scores" not in result:
                    result["scores"] = {"total": 0}
                if "dimensions" not in result["scores"]:
                    result["scores"]["dimensions"] = {}
                
                # 映射中文分项到英文维度
                dimension_mapping = {
                    "内容主旨": "content",
                    "语言文采": "language",
                    "文章结构": "structure",
                    "文面书写": "grammar"
                }
                
                for cn_dim, en_dim in dimension_mapping.items():
                    if cn_dim in raw_data["分项得分"]:
                        try:
                            score = float(raw_data["分项得分"][cn_dim])
                            result["scores"]["dimensions"][en_dim] = score
                        except (ValueError, TypeError):
                            result["scores"]["dimensions"][en_dim] = 0
            
            # 处理分析文本
            analyses_mapping = {
                "总体评价": "summary",
                "内容分析": "content",
                "语言分析": "language",
                "结构分析": "structure"
            }
            
            if "analyses" not in result:
                result["analyses"] = {}
            
            for cn_field, en_field in analyses_mapping.items():
                if cn_field in raw_data:
                    result["analyses"][en_field] = raw_data[cn_field]
            
            # 处理反馈
            if "feedback" not in result:
                result["feedback"] = {}
            
            if "写作建议" in raw_data:
                if isinstance(raw_data["写作建议"], list):
                    result["feedback"]["improvements"] = raw_data["写作建议"]
                elif isinstance(raw_data["写作建议"], str):
                    result["feedback"]["improvements"] = [raw_data["写作建议"]]
            
            if "错别字" in raw_data:
                result["feedback"]["corrections"] = raw_data["错别字"] if isinstance(raw_data["错别字"], list) else []
                
        # 确保维度分数存在
        required_dimensions = ["content", "language", "structure", "grammar"]
        if "scores" in result and "dimensions" in result["scores"]:
            for dim in required_dimensions:
                if dim not in result["scores"]["dimensions"]:
                    result["scores"]["dimensions"][dim] = 0
    
    def _get_default_structure(self) -> Dict[str, Any]:
        """
        获取默认结果结构
        
        Returns:
            Dict[str, Any]: 默认结果结构
        """
        return copy.deepcopy(self.core_fields) 