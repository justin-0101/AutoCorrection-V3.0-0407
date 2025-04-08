import logging
from unittest.mock import MagicMock

logger = logging.getLogger('app.core.services')

class MockAIClientFactory:
    """模拟AI客户端工厂"""
    def get_client(self, provider=None):
        mock_client = MagicMock()
        mock_client.generate.return_value = "这是一个模拟的AI响应"
        return mock_client

class MockRedisService:
    """模拟Redis服务"""
    def __init__(self):
        self._data = {}
        
    def get(self, key):
        return self._data.get(key)
        
    def set(self, key, value, ex=None):
        self._data[key] = value
        
    def delete(self, key):
        self._data.pop(key, None)

class MockCorrectionService:
    """模拟批改服务"""
    def perform_correction(self, essay_id):
        return {
            'status': 'success',
            'essay_id': essay_id,
            'results': {
                'total_score': 85,
                'content_score': 80,
                'language_score': 90,
                'suggestions': ['这是一个模拟的批改建议']
            }
        }

class MockSourceTypeManager:
    """模拟来源类型管理器"""
    def __init__(self):
        self.types = {
            'text': {'name': '文本输入', 'enabled': True},
            'paste': {'name': '粘贴', 'enabled': True},
            'upload': {'name': '上传', 'enabled': True},
            'api': {'name': 'API', 'enabled': True}
        }
    
    def get_type(self, type_name):
        return self.types.get(type_name)
    
    def is_type_enabled(self, type_name):
        type_info = self.types.get(type_name)
        return type_info and type_info['enabled']

def get_mock_services():
    """获取所有模拟服务的实例"""
    return {
        'ai_client_factory': MockAIClientFactory(),
        'redis_service': MockRedisService(),
        'correction_service': MockCorrectionService(),
        'source_type_manager': MockSourceTypeManager()
    } 