#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件服务模块，提供统一的文件处理和元数据管理接口
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from app.utils.file_handler import FileHandler
from app.core.services.container import ServiceContainer

# 创建logger实例
logger = logging.getLogger(__name__)

class FileService:
    """
    文件服务，提供统一的文件管理接口
    负责文件元数据管理和文件操作的抽象
    """
    
    def __init__(self):
        """初始化文件服务"""
        self.file_handler = FileHandler()
        self._file_metadata_cache = {}  # 内存缓存，用于存储文件元数据
    
    def create_file_metadata(self, essay_id: int, file_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建文件元数据
        
        Args:
            essay_id: 作文ID
            file_result: 文件处理结果
            
        Returns:
            Dict: 文件元数据
        """
        if not file_result:
            return None
            
        metadata = {
            'essay_id': essay_id,
            'file_name': file_result.get('original_filename'),
            'file_path': file_result.get('path'),
            'mime_type': file_result.get('mime_type'),
            'size': file_result.get('size'),
            'created_at': datetime.now().isoformat()
        }
        
        # 存入缓存
        self._file_metadata_cache[str(essay_id)] = metadata
        logger.debug(f"已创建文件元数据: {metadata}")
        
        return metadata
    
    def get_metadata(self, essay_id: int) -> Dict[str, Any]:
        """
        获取文件元数据
        
        Args:
            essay_id: 作文ID
            
        Returns:
            Dict: 文件元数据
        """
        # 尝试从缓存获取
        metadata = self._file_metadata_cache.get(str(essay_id))
        if metadata:
            return metadata
            
        # 如果缓存中没有，返回空值
        logger.warning(f"未找到作文ID为 {essay_id} 的文件元数据")
        return {}
    
    def delete_file(self, essay_id: int) -> bool:
        """
        删除文件
        
        Args:
            essay_id: 作文ID
            
        Returns:
            bool: 是否成功删除
        """
        metadata = self.get_metadata(essay_id)
        if not metadata:
            logger.warning(f"未找到作文ID为 {essay_id} 的文件元数据，无法删除文件")
            return False
            
        file_path = metadata.get('file_path')
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"文件路径不存在: {file_path}")
            return False
            
        try:
            # 删除文件
            self.file_handler.delete_file(file_path)
            
            # 从缓存中移除
            self._file_metadata_cache.pop(str(essay_id), None)
            
            logger.info(f"成功删除文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"删除文件时发生错误: {str(e)}")
            return False
    
    def process_file(self, file_data, filename: str) -> Dict[str, Any]:
        """
        处理文件
        
        Args:
            file_data: 文件数据
            filename: 文件名
            
        Returns:
            Dict: 处理结果
        """
        return self.file_handler.process_file(file_data, filename)

# 注册服务
def register_file_service():
    """注册文件服务到容器"""
    container = ServiceContainer()
    container.register('file_service', FileService, scope='singleton')
    logger.info("文件服务已注册到服务容器") 