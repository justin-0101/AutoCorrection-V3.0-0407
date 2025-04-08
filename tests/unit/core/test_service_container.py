"""
服务容器单元测试
"""
import unittest
import redis
from unittest.mock import MagicMock, patch

from app.core.services.container import ServiceContainer
from app.core.services.redis_service import RedisService

class TestServiceContainer(unittest.TestCase):
    """测试服务容器类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建一个新的服务容器实例
        self.container = ServiceContainer()
        # 清除之前的注册服务
        self.container._services = {}
        self.container._factories = {}
    
    def test_singleton_pattern(self):
        """测试服务容器的单例模式"""
        container1 = ServiceContainer()
        container2 = ServiceContainer()
        
        # 应该是同一个实例
        self.assertIs(container1, container2)
    
    def test_register_and_get_service(self):
        """测试服务注册和获取"""
        # 创建模拟服务
        mock_service = MagicMock()
        
        # 注册服务
        self.container.register("test_service", mock_service)
        
        # 获取服务
        service = self.container.get("test_service")
        
        # 确认获取的是同一个服务
        self.assertIs(service, mock_service)
    
    def test_register_factory(self):
        """测试服务工厂注册"""
        # 创建模拟工厂函数
        mock_service = MagicMock()
        mock_factory = MagicMock(return_value=mock_service)
        
        # 注册工厂
        self.container.register_factory("factory_service", mock_factory)
        
        # 获取服务 - 应该调用工厂函数
        service = self.container.get("factory_service")
        
        # 确认工厂被调用且返回正确服务
        mock_factory.assert_called_once()
        self.assertIs(service, mock_service)
        
        # 再次获取服务 - 应该返回缓存的实例而不再次调用工厂
        mock_factory.reset_mock()
        service2 = self.container.get("factory_service")
        mock_factory.assert_not_called()
        self.assertIs(service2, mock_service)
    
    def test_get_nonexistent_service(self):
        """测试获取不存在的服务"""
        service = self.container.get("nonexistent")
        self.assertIsNone(service)
    
    def test_get_typed(self):
        """测试获取指定类型的服务"""
        # 创建测试服务
        class TestService:
            pass
        
        test_service = TestService()
        self.container.register("test_service", test_service)
        
        # 获取正确类型
        service = self.container.get_typed("test_service", TestService)
        self.assertIs(service, test_service)
        
        # 获取错误类型
        service = self.container.get_typed("test_service", dict)
        self.assertIsNone(service)
    
    def test_clear(self):
        """测试清除所有服务"""
        # 注册几个服务
        self.container.register("service1", MagicMock())
        self.container.register("service2", MagicMock())
        
        # 清除所有服务
        self.container.clear()
        
        # 确认服务已清除
        self.assertEqual(len(self.container._services), 0)
        self.assertIsNone(self.container.get("service1"))
        self.assertIsNone(self.container.get("service2"))
    
    @patch('importlib.import_module')
    def test_import_and_register(self, mock_import):
        """测试导入和注册服务"""
        # 模拟模块和类
        mock_class = MagicMock()
        mock_module = MagicMock()
        mock_module.TestClass = mock_class
        mock_import.return_value = mock_module
        
        # 导入并注册服务
        self.container.import_and_register("test.module", "TestClass")
        
        # 验证导入和注册
        mock_import.assert_called_once_with("test.module")
        mock_class.assert_called_once()
        self.assertIsNotNone(self.container.get("TestClass"))
        
        # 导入并注册服务(指定服务名)
        mock_import.reset_mock()
        mock_class.reset_mock()
        self.container.import_and_register("test.module", "TestClass", "custom_name")
        
        mock_import.assert_called_once_with("test.module")
        mock_class.assert_called_once()
        self.assertIsNotNone(self.container.get("custom_name"))

class TestRedisService(unittest.TestCase):
    """测试Redis服务类"""
    
    def setUp(self):
        """测试前准备"""
        # 清除实例状态
        RedisService._instance = None
    
    @patch('redis.Redis')
    def test_singleton_pattern(self, mock_redis):
        """测试Redis服务的单例模式"""
        # 设置mock返回，避免连接错误
        mock_redis.return_value.ping.return_value = True
        
        redis_service1 = RedisService()
        redis_service2 = RedisService()
        
        # 应该是同一个实例
        self.assertIs(redis_service1, redis_service2)
    
    @patch('redis.Redis')
    def test_initialize_from_env(self, mock_redis):
        """测试从环境变量初始化Redis连接"""
        # 设置mock返回，避免连接错误
        mock_redis.return_value.ping.return_value = True
        
        with patch.dict('os.environ', {'REDIS_URL': 'redis://testhost:1234/5'}):
            redis_service = RedisService()
            # 验证Redis连接被创建，使用了正确的参数
            mock_redis.assert_called()
            # 应该解析URL并传递参数
            call_kwargs = mock_redis.call_args[1]
            self.assertEqual(call_kwargs.get('host'), 'testhost')
            self.assertEqual(call_kwargs.get('port'), 1234)
            self.assertEqual(call_kwargs.get('db'), 5)
    
    @patch('redis.Redis')
    def test_connection_error_handling(self, mock_redis):
        """测试Redis连接错误处理"""
        # 模拟连接失败
        mock_redis.return_value.ping.side_effect = redis.exceptions.ConnectionError("连接失败")
        
        redis_service = RedisService()
        
        # 连接状态应该为False
        self.assertFalse(redis_service.is_connected())
    
    @patch('redis.Redis')
    def test_reconnect(self, mock_redis):
        """测试重新连接功能"""
        # 首先连接失败
        mock_redis.return_value.ping.side_effect = redis.exceptions.ConnectionError("连接失败")
        redis_service = RedisService()
        self.assertFalse(redis_service.is_connected())
        
        # 然后连接成功
        mock_redis.return_value.ping.side_effect = None
        mock_redis.return_value.ping.return_value = True
        
        # 尝试重连
        result = redis_service.reconnect()
        
        # 应该成功重连
        self.assertTrue(result)
        self.assertTrue(redis_service.is_connected())
    
    @patch('redis.Redis')
    def test_basic_operations(self, mock_redis):
        """测试基本Redis操作方法"""
        # 设置mock返回
        mock_redis.return_value.ping.return_value = True
        mock_redis.return_value.set.return_value = True
        mock_redis.return_value.get.return_value = "test_value"
        mock_redis.return_value.delete.return_value = 1
        mock_redis.return_value.hset.return_value = 1
        mock_redis.return_value.hget.return_value = "test_hash_value"
        mock_redis.return_value.hgetall.return_value = {"key1": "value1", "key2": "value2"}
        
        redis_service = RedisService()
        
        # 测试set方法
        self.assertTrue(redis_service.set("test_key", "test_value"))
        mock_redis.return_value.set.assert_called_with("test_key", "test_value", ex=None)
        
        # 测试get方法
        self.assertEqual(redis_service.get("test_key"), "test_value")
        mock_redis.return_value.get.assert_called_with("test_key")
        
        # 测试delete方法
        self.assertTrue(redis_service.delete("test_key"))
        mock_redis.return_value.delete.assert_called_with("test_key")
        
        # 测试hash_set方法
        self.assertTrue(redis_service.hash_set("test_hash", "field1", "value1"))
        mock_redis.return_value.hset.assert_called_with("test_hash", "field1", "value1")
        
        # 测试hash_get方法
        self.assertEqual(redis_service.hash_get("test_hash", "field1"), "test_hash_value")
        mock_redis.return_value.hget.assert_called_with("test_hash", "field1")
        
        # 测试hash_getall方法
        self.assertEqual(redis_service.hash_getall("test_hash"), {"key1": "value1", "key2": "value2"})
        mock_redis.return_value.hgetall.assert_called_with("test_hash")

if __name__ == "__main__":
    unittest.main() 