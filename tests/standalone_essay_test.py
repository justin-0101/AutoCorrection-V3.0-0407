#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
独立的Essay模型测试脚本
不依赖于pytest和conftest.py
"""

import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 导入所需模块
from app import create_app
from app.models.db import db
from app.models.essay import Essay, EssaySourceType
from app.utils.input_sanitizer import sanitize_input, sanitize_enum_input

class TestEssayModel(unittest.TestCase):
    """测试Essay模型，特别是source_type字段的功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.app = create_app('testing')
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
    
    def tearDown(self):
        """清理测试环境"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_source_type_default(self):
        """测试source_type默认值"""
        essay = Essay(title='测试标题', content='测试内容', user_id=1)
        db.session.add(essay)
        db.session.commit()
        
        self.assertEqual(essay.source_type, EssaySourceType.text.value)
    
    def test_source_type_enum_values(self):
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
            self.assertEqual(essays[i].source_type, source_type.value)
    
    def test_source_type_validation(self):
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
        
        self.assertEqual(essay1.source_type, 'paste')
        self.assertEqual(essay2.source_type, 'upload')
        self.assertEqual(essay3.source_type, 'text')
        self.assertEqual(essay4.source_type, 'api')
        self.assertEqual(essay5.source_type, 'text')  # 无效值应转为默认值
    
    def test_sanitize_input_integration(self):
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
            self.assertEqual(essays[i].source_type, expected)

if __name__ == '__main__':
    unittest.main() 