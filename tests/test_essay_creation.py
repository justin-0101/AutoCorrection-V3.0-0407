#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试作文创建流程
"""

import pytest
from datetime import datetime
from app.models.essay import Essay, EssayStatus, EssaySourceType
from app.models.correction import Correction, CorrectionStatus
from app.core.essay.essay_service import EssayService
from app.errors import ValidationError

def test_basic_essay_creation(app, db, test_user):
    """测试基本的作文创建功能"""
    with app.app_context():
        # 准备测试数据
        test_data = {
            'user_id': test_user.id,
            'title': '测试作文',
            'content': '这是一篇测试作文的内容。' * 10,  # 确保超过最小长度要求
            'grade': '高中',
            'author_name': '测试作者',
            'is_public': True
        }
        
        # 创建作文
        result = EssayService.create_essay(**test_data)
        
        # 验证返回结果
        assert result['status'] == 'success'
        assert 'essay_id' in result
        assert 'task_id' in result
        
        # 验证作文记录
        essay = Essay.query.get(result['essay_id'])
        assert essay is not None
        assert essay.title == test_data['title']
        assert essay.content == test_data['content']
        assert essay.status == EssayStatus.PENDING.value
        
        # 验证批改记录是否自动创建
        correction = Correction.query.filter_by(essay_id=essay.id).first()
        assert correction is not None
        assert correction.status == CorrectionStatus.PENDING.value

def test_essay_validation(app, db, test_user):
    """测试作文数据验证"""
    with app.app_context():
        # 测试空标题
        with pytest.raises(ValidationError) as exc:
            EssayService.create_essay(
                user_id=test_user.id,
                title='',
                content='测试内容' * 10
            )
        assert '标题不能为空' in str(exc.value)
        
        # 测试内容过短
        with pytest.raises(ValidationError) as exc:
            EssayService.create_essay(
                user_id=test_user.id,
                title='测试标题',
                content='短文'
            )
        assert '内容长度不能少于50个字符' in str(exc.value)

def test_transaction_integrity(app, db, test_user):
    """测试事务完整性"""
    with app.app_context():
        # 获取初始记录数
        initial_essay_count = Essay.query.count()
        initial_correction_count = Correction.query.count()
        
        # 创建作文
        result = EssayService.create_essay(
            user_id=test_user.id,
            title='事务测试',
            content='这是用于测试事务完整性的作文内容。' * 5
        )
        
        # 验证记录数的增加
        assert Essay.query.count() == initial_essay_count + 1
        assert Correction.query.count() == initial_correction_count + 1
        
        # 验证关联关系
        essay = Essay.query.get(result['essay_id'])
        correction = Correction.query.filter_by(essay_id=essay.id).first()
        assert correction is not None
        assert correction.essay_id == essay.id

def test_file_essay_creation(app, db, test_user):
    """测试从文件创建作文"""
    with app.app_context():
        # 模拟文件数据
        file_data = "这是一个测试文件的内容。" * 10
        filename = "test_essay.txt"
        
        # 创建作文
        result = EssayService.create_essay_from_file(
            user_id=test_user.id,
            file_data=file_data,
            filename=filename,
            grade='初中'
        )
        
        # 验证返回结果
        assert result['status'] == 'success'
        assert 'essay_id' in result
        
        # 验证作文记录
        essay = Essay.query.get(result['essay_id'])
        assert essay is not None
        assert essay.title == 'test_essay'  # 文件名作为标题
        assert essay.source_type == EssaySourceType.upload.value
        
        # 验证批改记录
        correction = Correction.query.filter_by(essay_id=essay.id).first()
        assert correction is not None 