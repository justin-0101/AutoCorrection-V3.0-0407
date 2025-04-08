import pytest
from app.utils.input_sanitizer import sanitize_input, sanitize_enum_input
from app.models.essay import EssaySourceType
import enum

class TestInputSanitizer:
    """测试输入清理工具函数"""
    
    def test_sanitize_input_basic(self):
        """测试基本清理功能"""
        assert sanitize_input("test") == "test"
        assert sanitize_input(" test ") == "test"
        assert sanitize_input("TEST") == "test"
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""
    
    def test_sanitize_input_max_length(self):
        """测试长度限制功能"""
        long_input = "a" * 100
        assert len(sanitize_input(long_input, max_length=10)) == 10
        assert sanitize_input(long_input, max_length=5) == "aaaaa"
        
        # 确保不截断正常长度的输入
        assert sanitize_input("normal", max_length=10) == "normal"
    
    def test_sanitize_input_default(self):
        """测试默认值功能"""
        assert sanitize_input("", default="default") == "default"
        assert sanitize_input(None, default="default") == "default"
        
        # 空白字符被清理后为空字符串，应返回默认值
        assert sanitize_input("   ", default="default") == "default"
    
    def test_sanitize_input_whitespace(self):
        """测试空白字符处理"""
        # 允许空白
        assert sanitize_input("test with spaces", allow_whitespace=True) == "test with spaces"
        
        # 不允许空白
        assert sanitize_input("test with spaces", allow_whitespace=False) == "testwithspaces"
        
        # 处理前后空白
        assert sanitize_input("  leading and trailing  ") == "leading and trailing"
    
    def test_sanitize_input_lowercase(self):
        """测试大小写处理"""
        # 默认转小写
        assert sanitize_input("UPPERCASE") == "uppercase"
        
        # 保留大小写
        assert sanitize_input("MixedCase", lowercase=False) == "MixedCase"
    
    def test_sanitize_input_special_chars(self):
        """测试特殊字符处理"""
        # 处理控制字符
        assert sanitize_input("line1\nline2") == "line1line2"
        assert sanitize_input("tab\tseparated") == "tabseparated"
        
        # 处理Unicode特殊字符
        assert sanitize_input("zero-width\u200bspace") == "zero-widthspace"
        assert sanitize_input("zero-width\u200cnon-joiner") == "zero-widthnon-joiner"
    
    def test_sanitize_input_enum_values(self):
        """测试枚举值验证"""
        enum_values = ["apple", "banana", "cherry"]
        
        # 有效值
        assert sanitize_input("apple", enum_values=enum_values) == "apple"
        assert sanitize_input("BANANA", enum_values=enum_values) == "banana"
        
        # 无效值，返回空字符串
        assert sanitize_input("orange", enum_values=enum_values) == ""
        
        # 无效值，但提供了默认值
        assert sanitize_input("orange", enum_values=enum_values, default="apple") == "apple"
        
        # 模糊匹配
        assert sanitize_input("app", enum_values=enum_values) == "apple"
    
    def test_sanitize_enum_input(self):
        """测试枚举输入处理"""
        # 定义测试枚举
        class TestEnum(enum.Enum):
            APPLE = "apple"
            BANANA = "banana"
            CHERRY = "cherry"
        
        # 使用枚举实例
        assert sanitize_enum_input(TestEnum.APPLE, TestEnum) == TestEnum.APPLE
        
        # 使用枚举值
        assert sanitize_enum_input("apple", TestEnum) == TestEnum.APPLE
        
        # 使用大写枚举名
        assert sanitize_enum_input("BANANA", TestEnum) == TestEnum.BANANA
        
        # 使用无效值，返回默认值None
        assert sanitize_enum_input("orange", TestEnum) is None
        
        # 使用无效值，但提供默认值
        assert sanitize_enum_input("orange", TestEnum, TestEnum.CHERRY) == TestEnum.CHERRY
    
    def test_sanitize_enum_input_essay_source_type(self):
        """测试使用实际枚举类型EssaySourceType"""
        # 使用枚举实例
        assert sanitize_enum_input(EssaySourceType.text, EssaySourceType) == EssaySourceType.text
        
        # 使用枚举值
        assert sanitize_enum_input("paste", EssaySourceType) == EssaySourceType.paste
        
        # 使用大写
        assert sanitize_enum_input("UPLOAD", EssaySourceType) == EssaySourceType.upload
        
        # 使用无效值，返回默认值
        assert sanitize_enum_input("invalid", EssaySourceType, EssaySourceType.text) == EssaySourceType.text

    @pytest.mark.parametrize("input_value,expected", [
        ("text", "text"),
        (" text ", "text"),
        ("TEXT", "text"),
        ("", ""),
        (None, ""),
        (123, "123"),
        (True, "true"),
    ])
    def test_sanitize_input_types(self, input_value, expected):
        """参数化测试不同类型的输入"""
        assert sanitize_input(input_value) == expected 