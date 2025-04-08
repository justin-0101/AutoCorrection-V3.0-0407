import pytest
from app.models.essay import Essay, EssaySourceType
from app.models.db import db
from app.utils.input_sanitizer import sanitize_input, sanitize_enum_input
import unittest

class TestEssayModel:
    """测试Essay模型，特别是source_type字段的功能"""
    
    def test_source_type_default(self, app, db):
        """测试source_type默认值"""
        essay = Essay(title='测试标题', content='测试内容', user_id=1)
        db.session.add(essay)
        db.session.commit()
        
        assert essay.source_type == EssaySourceType.text.value
    
    def test_source_type_enum_values(self, app, db):
        """测试source_type枚举的所有值"""
        # 创建使用不同枚举值的Essay对象
        essays = []
        for source_type in EssaySourceType:
            essay = Essay(
                title=f'测试{source_type.name}',
                content=f'这是{source_type.name}类型的测试内容',
                user_id=1,
                source_type=source_type.value
            )
            essays.append(essay)
            
        db.session.add_all(essays)
        db.session.commit()
        
        # 验证所有值是否正确保存
        for i, source_type in enumerate(EssaySourceType):
            assert essays[i].source_type == source_type.value
    
    def test_source_type_validation(self, app, db):
        """测试source_type验证逻辑"""
        # 使用字符串值
        essay1 = Essay(title='测试1', content='内容1', user_id=1, 
                       source_type='paste')
        
        # 使用枚举对象
        essay2 = Essay(title='测试2', content='内容2', user_id=1,
                       source_type=EssaySourceType.upload)
        
        # 使用大写字符串
        essay3 = Essay(title='测试3', content='内容3', user_id=1,
                       source_type='TEXT')
        
        # 使用带空格字符串
        essay4 = Essay(title='测试4', content='内容4', user_id=1,
                       source_type=' api ')
        
        # 使用无效值
        essay5 = Essay(title='测试5', content='内容5', user_id=1,
                       source_type='invalid_type')
        
        db.session.add_all([essay1, essay2, essay3, essay4, essay5])
        db.session.commit()
        
        assert essay1.source_type == 'paste'
        assert essay2.source_type == 'upload'  # 现在应该正确处理枚举对象
        assert essay3.source_type == 'text'
        assert essay4.source_type == 'api'
        assert essay5.source_type == 'text'  # 无效值应转为默认值
    
    def test_sanitize_input_integration(self, app, db):
        """测试输入清理函数与Essay模型的集成"""
        problematic_inputs = [
            'paste\u200b',  # 带零宽空格
            'upload\n',     # 带换行符
            ' TEXT\t',      # 带空格和制表符
            'API\u200c',    # 带零宽不连字符
            '文本'           # 非英文字符
        ]
        
        expected_outputs = [
            'paste',
            'upload',
            'text',
            'api',
            'text'  # 非英文应返回默认值
        ]
        
        essays = []
        for i, input_value in enumerate(problematic_inputs):
            essay = Essay(
                title=f'清理测试{i}',
                content=f'测试内容{i}',
                user_id=1,
                source_type=input_value
            )
            essays.append(essay)
        
        db.session.add_all(essays)
        db.session.commit()
        
        # 验证清理后的值
        for i, expected in enumerate(expected_outputs):
            assert essays[i].source_type == expected
    
    def test_source_type_manager_integration(self, app, db):
        """测试SourceTypeManager与Essay模型的集成"""
        from app.core.source_type_manager import SourceTypeManager
        
        # 验证默认类型可用
        default_type = SourceTypeManager.get_default_type()
        assert default_type == 'text'
        
        # 验证注册的类型
        types = SourceTypeManager.get_types()
        assert 'text' in types
        assert 'paste' in types
        assert 'upload' in types
        assert 'api' in types
        
        # 测试归一化函数
        normalized = SourceTypeManager.normalize_type('PASTE')
        assert normalized == 'paste'
        
        # 测试验证函数
        assert SourceTypeManager.is_valid_type('text')
        assert not SourceTypeManager.is_valid_type('invalid')
        
        # 创建使用归一化类型的Essay
        essay = Essay(
            title='归一化测试',
            content='测试内容',
            user_id=1,
            source_type=SourceTypeManager.normalize_type('UPLOAD')
        )
        db.session.add(essay)
        db.session.commit()
        
        assert essay.source_type == 'upload'

    @pytest.mark.parametrize("input_value,expected", [
        ('text', 'text'),
        ('PASTE', 'paste'),
        (' upload ', 'upload'),
        ('api\n', 'api'),
        ('invalid', 'text'),
        ('', 'text'),
        (None, 'text'),
        (EssaySourceType.paste, 'paste'),
    ])
    def test_source_type_parameterized(self, app, db, input_value, expected):
        """参数化测试不同的source_type输入值"""
        essay = Essay(
            title='参数化测试',
            content='测试内容',
            user_id=1,
            source_type=input_value
        )
        db.session.add(essay)
        db.session.commit()
        
        assert essay.source_type == expected 