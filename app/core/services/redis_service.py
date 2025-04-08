"""
Redis服务模块
提供Redis连接和操作接口
"""
import os
import logging
import redis
from typing import Optional, Dict, Any, List, Union

logger = logging.getLogger(__name__)

class MockRedis:
    """Redis的模拟实现，用于Redis服务器不可用时"""
    def __init__(self):
        self.data = {}
        self.hash_data = {}
        logger.info("使用Redis模拟实现")
    
    def ping(self):
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, ex=None):
        self.data[key] = value
        return True
    
    def setex(self, key, time, value):
        """设置键值对并指定过期时间"""
        self.data[key] = value
        return True
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
        return True
    
    def hset(self, name, key, value):
        if name not in self.hash_data:
            self.hash_data[name] = {}
        self.hash_data[name][key] = value
        return True
    
    def hget(self, name, key):
        if name in self.hash_data and key in self.hash_data[name]:
            return self.hash_data[name][key]
        return None
    
    def hgetall(self, name):
        return self.hash_data.get(name, {})

class RedisService:
    """
    Redis服务类
    提供Redis连接和基本操作方法
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
            cls._instance._client = None
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize_from_env()
            self._initialized = True
    
    def _initialize_from_env(self) -> None:
        """
        从环境变量初始化Redis连接
        """
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        redis_password = os.environ.get('REDIS_PASSWORD', None)
        
        try:
            # 尝试连接真实的Redis
            self._client = redis.from_url(
                redis_url,
                password=redis_password,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                decode_responses=True
            )
            # 测试连接
            self._client.ping()
            logger.info(f"Redis连接成功: {redis_url}")
        except redis.exceptions.RedisError as e:
            logger.warning(f"Redis连接失败: {str(e)}")
            # 创建一个模拟的Redis客户端
            self._client = MockRedis()
            logger.info("使用模拟Redis客户端")
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """
        获取Redis客户端实例
        
        Returns:
            redis.Redis: Redis客户端实例，如果连接失败则返回MockRedis
        """
        return self._client
    
    def is_connected(self) -> bool:
        """
        检查Redis是否已连接
        
        Returns:
            bool: 是否连接成功
        """
        if self._client is None:
            return False
        
        try:
            self._client.ping()
            return True
        except redis.exceptions.RedisError:
            # 如果是MockRedis，将始终返回True
            if isinstance(self._client, MockRedis):
                return True
            return False
    
    def get(self, key: str) -> Optional[str]:
        """
        获取字符串值
        
        Args:
            key: 键名
            
        Returns:
            str: 获取的值，如果不存在则返回None
        """
        if not self.is_connected():
            logger.warning("Redis未连接，无法获取值")
            return None
        
        try:
            return self._client.get(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis获取值失败: {str(e)}")
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        设置字符串值
        
        Args:
            key: 键名
            value: 值
            ex: 过期时间(秒)
            
        Returns:
            bool: 是否设置成功
        """
        if not self.is_connected():
            logger.warning("Redis未连接，无法设置值")
            return False
        
        try:
            self._client.set(key, value, ex=ex)
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis设置值失败: {str(e)}")
            return False
    
    def setex(self, key: str, time: int, value: str) -> bool:
        """
        设置键值对并指定过期时间
        
        Args:
            key: 键名
            time: 过期时间(秒)
            value: 值
            
        Returns:
            bool: 是否设置成功
        """
        if not self.is_connected():
            logger.warning("Redis未连接，无法设置值")
            return False
        
        try:
            self._client.setex(key, time, value)
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis设置值失败: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除键
        
        Args:
            key: 键名
            
        Returns:
            bool: 是否删除成功
        """
        if not self.is_connected():
            logger.warning("Redis未连接，无法删除键")
            return False
        
        try:
            self._client.delete(key)
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis删除键失败: {str(e)}")
            return False
    
    def hash_set(self, name: str, key: str, value: str) -> bool:
        """
        设置哈希表中的字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 字段值
            
        Returns:
            操作是否成功
        """
        if not self.is_connected():
            logger.error("Redis未连接，无法设置哈希表字段")
            return False
        
        try:
            return bool(self._client.hset(name, key, value))
        except Exception as e:
            logger.error(f"设置Redis哈希表字段失败: {str(e)}")
            return False
    
    def hash_get(self, name: str, key: str) -> Optional[str]:
        """
        获取哈希表中的字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            字段值，如果不存在则返回None
        """
        if not self.is_connected():
            logger.error("Redis未连接，无法获取哈希表字段")
            return None
        
        try:
            return self._client.hget(name, key)
        except Exception as e:
            logger.error(f"获取Redis哈希表字段失败: {str(e)}")
            return None
    
    def hash_getall(self, name: str) -> Dict[str, str]:
        """
        获取哈希表中的所有字段和值
        
        Args:
            name: 哈希表名
            
        Returns:
            字段名和值的字典
        """
        if not self.is_connected():
            logger.error("Redis未连接，无法获取哈希表所有字段")
            return {}
        
        try:
            return self._client.hgetall(name)
        except Exception as e:
            logger.error(f"获取Redis哈希表所有字段失败: {str(e)}")
            return {} 