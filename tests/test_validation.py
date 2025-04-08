#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单的测试脚本，验证Essay模型的source_type字段
"""

import os
import sys
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

try:
    # 导入所需模块
    print("正在导入模块...")
    from app import create_app
    print("导入create_app成功")
    from app.models.db import db
    print("导入db成功")
    from app.models.essay import Essay, EssaySourceType
    print("导入Essay模型成功")
    from app.utils.input_sanitizer import sanitize_input, sanitize_enum_input
    print("导入sanitize函数成功")
except Exception as e:
    print(f"导入错误: {e}")
    traceback.print_exc()
    sys.exit(1)

def test_source_type():
    """测试source_type字段和验证逻辑"""
    try:
        # 创建测试Flask应用和上下文
        print("创建Flask应用...")
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        
        with app.app_context():
            # 创建数据库表
            print("创建数据库表...")
            db.create_all()
            
            # 测试1: 默认值
            print("\n开始测试1: 默认值")
            essay1 = Essay(title='测试1', content='内容1', user_id=1)
            db.session.add(essay1)
            db.session.commit()
            print(f"测试1 - 默认值: {essay1.source_type}, 预期: {EssaySourceType.text.value}")
            assert essay1.source_type == EssaySourceType.text.value
            
            # 测试2: 使用字符串值
            print("\n开始测试2: 字符串值")
            essay2 = Essay(title='测试2', content='内容2', user_id=1, source_type='paste')
            db.session.add(essay2)
            db.session.commit()
            print(f"测试2 - 字符串值: {essay2.source_type}, 预期: paste")
            assert essay2.source_type == 'paste'
            
            # 测试3: 使用枚举对象
            print("\n开始测试3: 枚举对象")
            enum_val = EssaySourceType.upload
            print(f"枚举对象类型: {type(enum_val)}, 名称: {enum_val.name}, 值: {enum_val.value}")
            print(f"是否是EssaySourceType的实例: {isinstance(enum_val, EssaySourceType)}")
            
            essay3 = Essay(title='测试3', content='内容3', user_id=1)
            # 直接设置属性而不是通过__init__
            essay3.source_type = enum_val.value  # 使用枚举值而不是枚举对象
            db.session.add(essay3)
            db.session.commit()
            print(f"测试3 - 枚举值: {essay3.source_type}, 预期: upload")
            assert essay3.source_type == 'upload'
            
            # 测试4: 直接测试__init__中使用枚举对象
            print("\n开始测试4: __init__中使用枚举对象")
            enum_val2 = EssaySourceType.api
            print(f"枚举对象类型: {type(enum_val2)}, 名称: {enum_val2.name}, 值: {enum_val2.value}")
            
            essay4 = Essay(title='测试4', content='内容4', user_id=1, source_type=enum_val2)
            db.session.add(essay4)
            db.session.commit()
            print(f"测试4 - 枚举对象: {essay4.source_type}, 预期: api")
            assert essay4.source_type == 'api'
            
            # 测试5: 使用无效值
            print("\n开始测试5: 无效值")
            essay5 = Essay(title='测试5', content='内容5', user_id=1, source_type='invalid')
            db.session.add(essay5)
            db.session.commit()
            print(f"测试5 - 无效值: {essay5.source_type}, 预期: {EssaySourceType.text.value}")
            assert essay5.source_type == EssaySourceType.text.value
            
            # 测试6: 使用特殊字符
            print("\n开始测试6: 特殊字符")
            problematic_input = 'paste\u200b'  # 带零宽空格
            essay6 = Essay(title='测试6', content='内容6', user_id=1, source_type=problematic_input)
            db.session.add(essay6)
            db.session.commit()
            print(f"测试6 - 特殊字符: {essay6.source_type}, 预期: paste")
            assert essay6.source_type == 'paste'
            
            print("\n所有测试通过！")
    except Exception as e:
        print(f"测试过程中出错: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_source_type() 