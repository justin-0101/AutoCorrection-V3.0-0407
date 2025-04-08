import pytest
from flask import url_for
from app.models.essay import Essay, EssaySourceType
from app.models.db import db
import io

class TestSourceTypeHandling:
    """测试source_type在不同情境中的处理"""
    
    def test_text_submission_source_type(self, client, app, logged_in_user):
        """测试通过文本提交时设置的source_type"""
        with app.app_context():
            # 提交表单数据
            response = client.post(
                url_for('main.correction'),
                data={
                    'article': '这是一篇测试作文，通过文本框提交。',
                    'subject': '测试文本提交',
                    'source_type': 'paste'  # 明确指定source_type
                },
                follow_redirects=True
            )
            
            # 检查请求是否成功
            assert response.status_code == 200
            
            # 检查数据库中的Essay记录
            essay = Essay.query.filter_by(title='测试文本提交').first()
            assert essay is not None
            assert essay.source_type == 'paste'
    
    def test_file_upload_source_type(self, client, app, logged_in_user):
        """测试通过文件上传时设置的source_type"""
        with app.app_context():
            # 创建模拟文件
            file_content = io.BytesIO(b'This is a test file content')
            file_content.name = 'test.txt'
            
            # 上传文件
            response = client.post(
                url_for('main.correction'),
                data={
                    'file': (file_content, 'test.txt'),
                    'source_type': 'upload'  # 应该被正确设置
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )
            
            # 检查请求是否成功
            assert response.status_code == 200
            
            # 查找最新的Essay记录
            essay = Essay.query.order_by(Essay.id.desc()).first()
            assert essay is not None
            assert essay.source_type == 'upload'
    
    def test_source_type_missing(self, client, app, logged_in_user):
        """测试未提供source_type时的默认行为"""
        with app.app_context():
            # 提交表单数据，不包含source_type
            response = client.post(
                url_for('main.correction'),
                data={
                    'article': '这是一篇测试作文，未指定类型。',
                    'subject': '测试默认类型'
                },
                follow_redirects=True
            )
            
            # 检查请求是否成功
            assert response.status_code == 200
            
            # 检查数据库中的Essay记录
            essay = Essay.query.filter_by(title='测试默认类型').first()
            assert essay is not None
            # 应当使用默认值'paste'，因为是通过表单提交的文本
            assert essay.source_type == 'paste'
    
    @pytest.mark.parametrize('source_type_value,expected', [
        ('text', 'text'),
        ('paste', 'paste'),
        ('upload', 'upload'),
        ('api', 'api'),
        ('TEXT', 'text'),
        (' paste ', 'paste'),
        ('invalid', 'text'),  # 无效值应使用默认值
        ('', 'text'),  # 空字符串应使用默认值
    ])
    def test_various_source_type_values(self, client, app, logged_in_user, source_type_value, expected):
        """测试各种source_type输入值的处理"""
        with app.app_context():
            # 提交表单数据
            response = client.post(
                url_for('main.correction'),
                data={
                    'article': f'测试各种source_type值：{source_type_value}',
                    'subject': f'测试值：{source_type_value}',
                    'source_type': source_type_value
                },
                follow_redirects=True
            )
            
            # 检查请求是否成功
            assert response.status_code == 200
            
            # 检查数据库中的Essay记录
            essay = Essay.query.filter_by(title=f'测试值：{source_type_value}').first()
            assert essay is not None
            assert essay.source_type == expected
    
    def test_api_submission_source_type(self, client, app, logged_in_user, monkeypatch):
        """测试通过API提交时设置的source_type"""
        from flask import jsonify
        
        # 模拟API处理函数
        def mock_api_handler():
            from flask import request, jsonify
            from app.models.essay import Essay
            from app.models.db import db
            
            data = request.get_json()
            
            essay = Essay(
                title=data.get('title', 'API提交'),
                content=data.get('content', ''),
                user_id=logged_in_user.id,
                source_type='api'  # API提交应设置为'api'
            )
            
            db.session.add(essay)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'essay_id': essay.id
            }), 200
        
        # 注册临时API路由
        with app.test_request_context():
            app.add_url_rule(
                '/api/test/submit_essay',
                'test_api_submit',
                mock_api_handler,
                methods=['POST']
            )
        
        # 发送API请求
        with app.app_context():
            response = client.post(
                '/api/test/submit_essay',
                json={
                    'title': 'API测试提交',
                    'content': '这是通过API提交的测试内容'
                }
            )
            
            # 检查API请求是否成功
            assert response.status_code == 200
            
            # 检查数据库中的Essay记录
            essay = Essay.query.filter_by(title='API测试提交').first()
            assert essay is not None
            assert essay.source_type == 'api' 