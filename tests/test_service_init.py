"""
测试服务初始化流程
"""
import pytest
import logging
from unittest.mock import Mock, patch
from flask import Flask

from app.core.services import (
    init_services, get_redis_service, get_ai_client_factory,
    get_correction_service, container
)
from app.core.services.container import ServiceScope
from app.core.services.redis_service import RedisService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def app():
    """创建测试用Flask应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def mock_db():
    """模拟数据库连接"""
    with patch('app.models.db.db') as mock:
        conn = Mock()
        conn.execute.return_value = Mock()
        conn.commit.return_value = None
        mock.engine.connect.return_value.__enter__.return_value = conn
        mock.text = lambda x: x
        yield mock

@pytest.fixture
def mock_redis_service(monkeypatch):
    """模拟Redis服务"""
    # 禁用RedisService的单例模式
    monkeypatch.setattr(RedisService, '_instance', None)
    with patch('app.core.services.redis_service.RedisService') as mock:
        instance = Mock()
        instance.is_connected.return_value = True
        mock.return_value = instance
        yield instance

@pytest.fixture
def mock_ai_factory():
    """模拟AI客户端工厂"""
    with patch('app.core.ai.AIClientFactory') as mock:
        instance = mock.return_value
        instance.get_client.return_value = Mock()
        yield instance

@pytest.fixture
def mock_correction_service():
    """模拟批改服务"""
    with patch('app.core.correction.correction_service.CorrectionService') as mock:
        instance = mock.return_value
        yield instance

def test_init_database(app, mock_db):
    """测试数据库初始化"""
    with app.app_context():
        from app.core.services import _init_database
        assert _init_database() == True
        mock_db.engine.connect.assert_called_once()

def test_service_initialization_order(app, mock_db, mock_redis_service, mock_ai_factory, mock_correction_service):
    """测试服务初始化顺序"""
    with app.app_context():
        # 清理容器
        container._services.clear()
        container._initialized = False
        
        # 执行初始化
        init_services()
        
        # 验证服务是否按正确顺序注册
        services = list(container._services.keys())
        assert services == ['redis_service', 'ai_client_factory', 'correction_service']
        
        # 验证服务作用域
        assert container._services['redis_service'].scope == ServiceScope.SINGLETON
        assert container._services['ai_client_factory'].scope == ServiceScope.SINGLETON
        assert container._services['correction_service'].scope == ServiceScope.SINGLETON

def test_service_getters(app, mock_db, mock_redis_service, mock_ai_factory, mock_correction_service):
    """测试服务获取函数"""
    with app.app_context():
        # 清理容器
        container._services.clear()
        container._initialized = False
        
        # 初始化服务
        init_services()
        
        # 测试各个getter函数
        assert get_redis_service() is not None
        assert get_ai_client_factory() is not None
        assert get_correction_service() is not None

def test_service_dependencies(app, mock_db, mock_redis_service, mock_ai_factory, mock_correction_service):
    """测试服务依赖关系验证"""
    with app.app_context():
        from app.core.services import _verify_service_dependencies
        
        # 清理容器
        container._services.clear()
        container._initialized = False
        
        # 初始化服务
        init_services()
        
        # 验证依赖关系
        assert _verify_service_dependencies() == True

def test_error_handling(app):
    """测试错误处理"""
    with app.app_context():
        # 清理容器
        container._services.clear()
        container._initialized = False
        
        # 测试缺少服务时的错误处理
        with pytest.raises(RuntimeError) as exc:
            init_services()
        assert "Redis服务是必需的基础服务" in str(exc.value)

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 