#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis服务模块
提供Redis连接和操作的封装
"""

import logging
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class RedisService:
    """Redis服务类，提供Redis操作的封装"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None):
        """
        初始化Redis服务
        
        Args:
            host: Redis主机地址
            port: Redis端口
            db: 数据库索引
            password: Redis密码
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client = None
        self._connect()
    
    def _connect(self):
        """建立Redis连接"""
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True  # 自动解码响应
            )
            # 测试连接
            self._client.ping()
            logger.info(f"Redis连接成功: {self.host}:{self.port}/{self.db}")
        except RedisError as e:
            logger.error(f"Redis连接失败: {str(e)}")
            self._client = None
    
    def get_client(self):
        """
        获取Redis客户端实例
        
        Returns:
            redis.Redis: Redis客户端实例
        """
        if not self._client:
            self._connect()
        return self._client
    
    def is_connected(self):
        """
        检查Redis连接状态
        
        Returns:
            bool: 是否已连接
        """
        try:
            if self._client:
                self._client.ping()
                return True
            return False
        except RedisError:
            return False
    
    def set(self, key, value, expire=None):
        """
        设置键值对
        
        Args:
            key: 键
            value: 值
            expire: 过期时间（秒）
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self._client:
                self._connect()
            if not self._client:
                return False
                
            self._client.set(key, value)
            if expire:
                self._client.expire(key, expire)
            return True
        except RedisError as e:
            logger.error(f"Redis设置键值对失败: {str(e)}")
            return False
    
    def setex(self, key, time, value):
        """
        设置键值对并指定过期时间
        
        Args:
            key: 键
            time: 过期时间(秒)
            value: 值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if not self._client:
                self._connect()
            if not self._client:
                return False
                
            self._client.setex(key, time, value)
            return True
        except RedisError as e:
            logger.error(f"Redis设置带过期时间的键值对失败: {str(e)}")
            return False
    
    def get(self, key):
        """
        获取键值
        
        Args:
            key: 键
            
        Returns:
            str: 值，如果不存在则返回None
        """
        try:
            if not self._client:
                self._connect()
            if not self._client:
                return None
                
            return self._client.get(key)
        except RedisError as e:
            logger.error(f"Redis获取键值失败: {str(e)}")
            return None
    
    def delete(self, key):
        """
        删除键
        
        Args:
            key: 键
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self._client:
                self._connect()
            if not self._client:
                return False
                
            return bool(self._client.delete(key))
        except RedisError as e:
            logger.error(f"Redis删除键失败: {str(e)}")
            return False
    
    def exists(self, key):
        """
        检查键是否存在
        
        Args:
            key: 键
            
        Returns:
            bool: 是否存在
        """
        try:
            if not self._client:
                self._connect()
            if not self._client:
                return False
                
            return bool(self._client.exists(key))
        except RedisError as e:
            logger.error(f"Redis检查键是否存在失败: {str(e)}")
            return False 