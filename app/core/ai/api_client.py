#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API客户端基类
提供统一的接口和错误处理逻辑
"""

import os
import json
import logging
import traceback
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple

# 配置日志
logger = logging.getLogger(__name__)

class APIError(Exception):
    """API调用异常"""
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class BaseAPIClient(ABC):
    """
    API客户端基类
    
    所有AI服务客户端都应继承此类，并实现其抽象方法。
    提供标准化的接口、错误处理和返回格式。
    """
    
    # 标准返回字段
    REQUIRED_RESULT_FIELDS = [
        "total_score", "content_score", "language_score", 
        "structure_score", "writing_score", "overall_assessment",
        "content_analysis", "language_analysis", "structure_analysis",
        "improvement_suggestions", "spelling_errors"
    ]
    
    def __init__(self, api_key: str = None, base_url: str = None, verify_ssl: bool = True):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            verify_ssl: 是否验证SSL证书
        """
        self.api_key = api_key
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        
        # 从环境变量加载配置
        self._load_config_from_env()
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"初始化{self.__class__.__name__}客户端")
    
    def _load_config_from_env(self):
        """从环境变量加载配置"""
        if not self.api_key:
            self.api_key = os.environ.get(f"{self.provider_name.upper()}_API_KEY")
        
        if not self.base_url:
            self.base_url = os.environ.get(f"{self.provider_name.upper()}_BASE_URL")
        
        # 环境变量中的SSL验证设置优先级更高
        ssl_verify = os.environ.get("VERIFY_SSL")
        if ssl_verify is not None:
            self.verify_ssl = ssl_verify.lower() not in ("false", "0", "no")
        
        # 为了兼容DISABLE_SSL_VERIFY环境变量
        disable_ssl = os.environ.get("DISABLE_SSL_VERIFY")
        if disable_ssl is not None:
            if disable_ssl.lower() in ("true", "1", "yes"):
                self.verify_ssl = False
    
    def _validate_config(self):
        """验证API配置"""
        if not self.api_key:
            logger.warning(f"{self.provider_name}客户端API密钥未配置")
        
        if not self.base_url:
            logger.warning(f"{self.provider_name}客户端基础URL未配置")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        提供商名称
        
        Returns:
            str: 提供商的标识名称，用于日志和配置
        """
        pass
    
    @abstractmethod
    def analyze_essay(self, content: str) -> Dict[str, Any]:
        """
        分析作文
        
        Args:
            content: 作文内容
            
        Returns:
            Dict: 分析结果，标准格式为：
            {
                "status": "success" | "error",
                "result": {
                    "total_score": 分数,
                    "content_score": 分数,
                    "language_score": 分数,
                    "structure_score": 分数,
                    "writing_score": 分数,
                    "overall_assessment": 评价文字,
                    "content_analysis": 内容分析,
                    "language_analysis": 语言分析,
                    "structure_analysis": 结构分析,
                    "improvement_suggestions": 改进建议,
                    "spelling_errors": {
                        "解析": [错误列表]
                    }
                } | {"message": 错误信息}
            }
        """
        pass
    
    def _api_request(self, endpoint: str, method: str = "GET", data: dict = None, params: dict = None,
                    headers: dict = None, timeout: int = 60, **kwargs) -> Dict:
        """
        发起API请求
        
        Args:
            endpoint: API端点
            method: 请求方法
            data: 请求数据
            params: 查询参数
            headers: 请求头
            timeout: 超时时间（秒）
            
        Returns:
            Dict: API响应
            
        Raises:
            APIError: API调用失败
        """
        # 构建完整URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # 准备请求头
        if headers is None:
            headers = {}
        
        # 添加通用的请求头
        headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })
        
        # 详细日志记录请求信息
        logger.debug(f"发送{method}请求到{url}")
        logger.info(f"完整请求URL: {url}")
        logger.info(f"请求方法: {method}")
        logger.info(f"请求头: {headers}")
        if params:
            logger.info(f"查询参数: {params}")
        if data:
            logger.info(f"请求数据: {json.dumps(data)[:500]}")
        
        try:
            response = requests.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
                verify=self.verify_ssl,
                timeout=timeout,
                **kwargs
            )
            
            # 记录响应状态码
            logger.info(f"响应状态码: {response.status_code}")
            
            # 尝试解析JSON响应
            try:
                result = response.json()
            except json.JSONDecodeError:
                result = {"text": response.text}
                logger.error(f"JSON解析失败: {response.text[:500]}")
            
            # 检查响应状态码
            if response.status_code >= 400:
                error_message = result.get("error", {}).get("message", f"API调用失败: {response.status_code}")
                logger.error(f"{self.provider_name} API错误: {error_message}")
                raise APIError(error_message, response.status_code, result)
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"{self.provider_name} API请求异常: {str(e)}")
            raise APIError(f"API连接失败: {str(e)}")
        except Exception as e:
            logger.error(f"{self.provider_name} API调用未知异常: {str(e)}\n{traceback.format_exc()}")
            raise APIError(f"API调用错误: {str(e)}")
    
    def format_response(self, response: Dict) -> Dict[str, Any]:
        """
        格式化API响应为统一格式
        
        Args:
            response: API原始响应
            
        Returns:
            Dict: 格式化的响应
        """
        try:
            result = self._extract_result(response)
            
            # 验证返回字段是否完整
            missing_fields = [field for field in self.REQUIRED_RESULT_FIELDS if field not in result]
            if missing_fields:
                logger.warning(f"{self.provider_name}响应缺少必要字段: {missing_fields}")
                
                # 为缺失字段添加默认值
                for field in missing_fields:
                    if field.endswith('_score'):
                        result[field] = 0
                    elif field == 'spelling_errors':
                        result[field] = {"解析": []}
                    else:
                        result[field] = ""
            
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.error(f"响应格式化错误: {str(e)}\n{traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"响应格式化错误: {str(e)}"
            }
    
    @abstractmethod
    def _extract_result(self, response: Dict) -> Dict[str, Any]:
        """
        从API响应中提取结果
        
        Args:
            response: API响应
            
        Returns:
            Dict: 提取的结果，必须包含REQUIRED_RESULT_FIELDS中定义的所有字段
        """
        pass

    def validate_response(self, response_data: Dict) -> Tuple[bool, List[str]]:
        """
        验证响应格式是否符合要求
        
        Args:
            response_data: 响应数据
            
        Returns:
            Tuple[bool, List[str]]: 
                - 是否有效（无缺失字段）
                - 缺失字段列表
        """
        missing_fields = []
        
        # 验证响应是否为字典
        if not isinstance(response_data, dict):
            return False, ["响应不是字典类型"]
        
        # 验证响应是否包含status字段
        if "status" not in response_data:
            return False, ["缺少status字段"]
        
        # 处理不同类型的响应
        if response_data["status"] == "success":
            # 成功响应应该包含result字段
            if "result" not in response_data:
                return False, ["缺少result字段"]
                
            # 继续验证result中的字段
            result = response_data["result"]
            if not isinstance(result, dict):
                return False, ["result不是字典类型"]
                
            # 验证是否包含所有必需字段
            for field in self.REQUIRED_RESULT_FIELDS:
                if field not in result:
                    missing_fields.append(field)
                    
        elif response_data["status"] == "error":
            # 错误响应应该包含message字段
            if "message" not in response_data:
                return False, ["错误响应缺少message字段"]
        
        return len(missing_fields) == 0, missing_fields 