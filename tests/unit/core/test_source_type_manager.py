import pytest
import os
import yaml
import tempfile
from app.core.source_type_manager import SourceTypeManager, create_default_config, init_source_types

class TestSourceTypeManager:
    """测试源类型管理器"""
    
    def setup_method(self):
        """每个测试方法前重置SourceTypeManager"""
        # 重置单例
        SourceTypeManager._instance = None
        # 重置类型
        SourceTypeManager._types = {'text', 'paste', 'upload', 'api'}
        # 重置配置
        SourceTypeManager._type_config = {
            'validation': {
                'case_sensitive': False,
                'allow_whitespace': False,
                'max_length': 20
            },
            'defaults': {
                'default_type': 'text',
                'fallback_type': 'text'
            }
        }
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = SourceTypeManager()
        manager2 = SourceTypeManager()
        
        assert manager1 is manager2
    
    def test_default_types(self):
        """测试默认类型集"""
        types = SourceTypeManager.get_types()
        
        assert 'text' in types
        assert 'paste' in types
        assert 'upload' in types
        assert 'api' in types
        assert len(types) == 4
    
    def test_register_type(self):
        """测试注册新类型"""
        # 注册新类型
        result = SourceTypeManager.register_type('email')
        
        assert result is True
        assert 'email' in SourceTypeManager.get_types()
        
        # 重复注册
        result = SourceTypeManager.register_type('email')
        assert result is True  # 重复注册也返回True
        
        # 注册无效类型
        result = SourceTypeManager.register_type('')
        assert result is False
        
        result = SourceTypeManager.register_type(None)
        assert result is False
    
    def test_unregister_type(self):
        """测试取消注册类型"""
        # 注册再取消
        SourceTypeManager.register_type('email')
        result = SourceTypeManager.unregister_type('email')
        
        assert result is True
        assert 'email' not in SourceTypeManager.get_types()
        
        # 无法删除默认类型
        result = SourceTypeManager.unregister_type('text')
        assert result is False
        assert 'text' in SourceTypeManager.get_types()
        
        # 取消不存在的类型
        result = SourceTypeManager.unregister_type('nonexistent')
        assert result is False
    
    def test_is_valid_type(self):
        """测试类型验证"""
        assert SourceTypeManager.is_valid_type('text') is True
        assert SourceTypeManager.is_valid_type('paste') is True
        assert SourceTypeManager.is_valid_type('invalid') is False
        assert SourceTypeManager.is_valid_type('') is False
        assert SourceTypeManager.is_valid_type(None) is False
        
        # 注册新类型后应当有效
        SourceTypeManager.register_type('email')
        assert SourceTypeManager.is_valid_type('email') is True
    
    def test_normalize_type(self):
        """测试类型归一化"""
        # 标准化大小写
        assert SourceTypeManager.normalize_type('TEXT') == 'text'
        
        # 标准化空白
        assert SourceTypeManager.normalize_type(' paste ') == 'paste'
        
        # 无效类型返回默认值
        assert SourceTypeManager.normalize_type('invalid') == 'text'
        
        # 空值返回默认值
        assert SourceTypeManager.normalize_type('') == 'text'
        assert SourceTypeManager.normalize_type(None) == 'text'
        
        # 模糊匹配
        assert SourceTypeManager.normalize_type('tex') == 'text'
    
    def test_create_enum_class(self):
        """测试创建枚举类"""
        # 注册额外类型
        SourceTypeManager.register_type('email')
        
        # 创建枚举
        enum_class = SourceTypeManager.create_enum_class()
        
        # 验证枚举内容
        assert hasattr(enum_class, 'TEXT')
        assert hasattr(enum_class, 'PASTE')
        assert hasattr(enum_class, 'UPLOAD')
        assert hasattr(enum_class, 'API')
        assert hasattr(enum_class, 'EMAIL')
        
        # 验证display_name属性
        instance = enum_class.TEXT
        assert instance.value == 'text'
        assert instance.display_name == '文本输入'
    
    def test_config_loading(self, tmp_path):
        """测试配置加载"""
        # 创建临时配置文件
        config_path = tmp_path / "test_config.yaml"
        config = {
            'allowed_types': ['text', 'paste', 'upload', 'api', 'voice'],
            'validation': {
                'case_sensitive': True,
                'max_length': 30
            },
            'defaults': {
                'default_type': 'paste'
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        # 加载配置
        result = SourceTypeManager.load_config(str(config_path))
        
        assert result is True
        assert 'voice' in SourceTypeManager.get_types()
        assert SourceTypeManager._type_config['validation']['case_sensitive'] is True
        assert SourceTypeManager._type_config['validation']['max_length'] == 30
        assert SourceTypeManager._type_config['defaults']['default_type'] == 'paste'
        assert SourceTypeManager._type_config['defaults']['fallback_type'] == 'text'  # 未修改的保持原值
    
    def test_create_default_config(self, tmp_path):
        """测试创建默认配置"""
        config_dir = tmp_path / "config"
        
        # 创建默认配置
        result = create_default_config(str(config_dir))
        
        assert result is True
        assert os.path.exists(os.path.join(config_dir, "source_types.yaml"))
        
        # 读取并验证配置内容
        with open(os.path.join(config_dir, "source_types.yaml"), 'r') as f:
            content = f.read()
            
        assert 'allowed_types:' in content
        assert 'text' in content
        assert 'paste' in content
        assert 'validation:' in content
    
    def test_init_source_types(self, monkeypatch):
        """测试初始化函数"""
        # 模拟函数调用
        mock_calls = []
        
        def mock_create_default_config():
            mock_calls.append('create_default_config')
            return True
            
        def mock_load_config():
            mock_calls.append('load_config')
            return True
        
        monkeypatch.setattr(
            'app.core.source_type_manager.create_default_config', 
            mock_create_default_config
        )
        monkeypatch.setattr(
            'app.core.source_type_manager.SourceTypeManager.load_config', 
            mock_load_config
        )
        
        # 调用初始化函数
        result = init_source_types()
        
        assert result is True
        assert 'create_default_config' in mock_calls
        assert 'load_config' in mock_calls 