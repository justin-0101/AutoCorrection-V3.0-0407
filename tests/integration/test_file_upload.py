"""
文件上传和处理集成测试
测试文件上传API和文件处理功能的集成
"""

import unittest
import os
import tempfile
import json
from io import BytesIO
from unittest.mock import patch, MagicMock

from flask import Flask
from werkzeug.datastructures import FileStorage

from app import create_app
from app.core.correction.file_service import FileService
from app.core.correction.ai_corrector import AICorrectionService
from app.models.user import User
from app.models.essay import Essay

class TestFileUploadIntegration(unittest.TestCase):
    """测试文件上传和处理的集成功能"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试应用
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        
        # 创建临时目录来存储上传文件
        self.upload_dir = tempfile.mkdtemp()
        self.app.config['UPLOAD_FOLDER'] = self.upload_dir
        
        # 获取测试客户端
        self.client = self.app.test_client()
        
        # 创建测试上下文
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # 模拟用户登录
        with self.app.test_request_context():
            self.test_user = User(
                username="testuser",
                email="test@example.com",
                is_active=True
            )
            self.test_user.set_password("password123")
            self.test_user.id = 1
            self.test_user.save = MagicMock()
            
            # 模拟登录状态
            with patch('flask_login.utils._get_user', return_value=self.test_user):
                self.login_context = self.client.session_transaction()
                self.login_context.__enter__()
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试文件
        for root, dirs, files in os.walk(self.upload_dir):
            for file in files:
                os.unlink(os.path.join(root, file))
        
        # 移除测试目录
        os.rmdir(self.upload_dir)
        
        # 清理上下文
        if hasattr(self, 'login_context') and self.login_context:
            self.login_context.__exit__(None, None, None)
        
        # 弹出应用上下文
        self.app_context.pop()
    
    @patch('app.routes.correction.FileService')
    def test_file_upload_txt_endpoint(self, mock_file_service_class):
        """测试TXT文件上传API端点"""
        # 模拟文件处理结果
        mock_file_service_instance = MagicMock()
        mock_file_service_instance.process_uploaded_file.return_value = {
            "success": True,
            "filename": "test_1234.txt",
            "file_path": "/path/to/uploads/test_1234.txt",
            "title": "测试文件",
            "content": "这是测试文本内容",
            "word_count": 8
        }
        mock_file_service_class.return_value = mock_file_service_instance
        
        # 准备文件数据
        test_file = FileStorage(
            stream=BytesIO(b"This is a test file content"),
            filename="test.txt",
            content_type="text/plain"
        )
        
        # 构建表单数据
        data = {
            'title': '测试文件',
            'file': test_file,
            'grade': 'junior'
        }
        
        # 发送请求
        response = self.client.post(
            '/api/v1/correction/upload',
            data=data,
            content_type='multipart/form-data'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        
        # 验证服务调用
        mock_file_service_instance.process_uploaded_file.assert_called_once()
    
    @patch('app.routes.correction.FileService')
    def test_file_upload_docx_endpoint(self, mock_file_service_class):
        """测试DOCX文件上传API端点"""
        # 模拟文件处理结果
        mock_file_service_instance = MagicMock()
        mock_file_service_instance.process_uploaded_file.return_value = {
            "success": True,
            "filename": "test_1234.docx",
            "file_path": "/path/to/uploads/test_1234.docx",
            "title": "测试文档",
            "content": "这是测试文档内容",
            "word_count": 8
        }
        mock_file_service_class.return_value = mock_file_service_instance
        
        # 准备文件数据
        test_file = FileStorage(
            stream=BytesIO(b"Mock DOCX content"),
            filename="test.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # 构建表单数据
        data = {
            'title': '测试文档',
            'file': test_file,
            'grade': 'senior'
        }
        
        # 发送请求
        response = self.client.post(
            '/api/v1/correction/upload',
            data=data,
            content_type='multipart/form-data'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        
        # 验证服务调用
        mock_file_service_instance.process_uploaded_file.assert_called_once()
    
    @patch('app.routes.correction.FileService')
    def test_file_upload_pdf_endpoint(self, mock_file_service_class):
        """测试PDF文件上传API端点"""
        # 模拟文件处理结果
        mock_file_service_instance = MagicMock()
        mock_file_service_instance.process_uploaded_file.return_value = {
            "success": True,
            "filename": "test_1234.pdf",
            "file_path": "/path/to/uploads/test_1234.pdf",
            "title": "测试PDF",
            "content": "这是从PDF提取的文本内容",
            "word_count": 11
        }
        mock_file_service_class.return_value = mock_file_service_instance
        
        # 准备文件数据
        test_file = FileStorage(
            stream=BytesIO(b"%PDF-1.5\nMock PDF content"),
            filename="test.pdf",
            content_type="application/pdf"
        )
        
        # 构建表单数据
        data = {
            'title': '测试PDF',
            'file': test_file,
            'grade': 'college'
        }
        
        # 发送请求
        response = self.client.post(
            '/api/v1/correction/upload',
            data=data,
            content_type='multipart/form-data'
        )
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        
        # 验证服务调用
        mock_file_service_instance.process_uploaded_file.assert_called_once()
    
    @patch('app.routes.correction.FileService')
    def test_file_upload_error_handling(self, mock_file_service_class):
        """测试文件上传错误处理"""
        # 模拟文件处理错误
        mock_file_service_instance = MagicMock()
        mock_file_service_instance.process_uploaded_file.side_effect = Exception("处理失败")
        mock_file_service_class.return_value = mock_file_service_instance
        
        # 准备文件数据
        test_file = FileStorage(
            stream=BytesIO(b"This is a test file content"),
            filename="test.txt",
            content_type="text/plain"
        )
        
        # 构建表单数据
        data = {
            'title': '测试文件',
            'file': test_file
        }
        
        # 发送请求
        response = self.client.post(
            '/api/v1/correction/upload',
            data=data,
            content_type='multipart/form-data'
        )
        
        # 验证错误响应
        self.assertEqual(response.status_code, 400)  # 或500，取决于错误处理
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    @patch('app.routes.correction.FileService')
    @patch('app.routes.correction.AICorrectionService')
    def test_complete_file_upload_correction_flow(self, mock_corrector_class, mock_file_service_class):
        """测试完整的文件上传和批改流程"""
        # 模拟文件处理结果
        mock_file_service_instance = MagicMock()
        mock_file_service_instance.process_uploaded_file.return_value = {
            "success": True,
            "filename": "test_1234.txt",
            "file_path": "/path/to/uploads/test_1234.txt",
            "title": "测试文件",
            "content": "这是测试文本内容",
            "word_count": 8
        }
        mock_file_service_class.return_value = mock_file_service_instance
        
        # 模拟批改结果
        mock_corrector_instance = MagicMock()
        mock_corrector_instance.correct_essay.return_value = {
            "status": "success",
            "result": {
                "total_score": 85,
                "content_score": 80,
                "language_score": 90,
                "structure_score": 85,
                "writing_score": 85,
                "overall_assessment": "这是一篇很好的作文",
                "content_analysis": "内容充实",
                "language_analysis": "语言流畅",
                "structure_analysis": "结构合理",
                "writing_analysis": "书写整洁",
                "improvement_suggestions": "可以进一步提高",
                "spelling_errors": {"错别字": []}
            }
        }
        mock_corrector_class.return_value = mock_corrector_instance
        
        # 模拟Essay模型
        mock_essay = MagicMock()
        mock_essay.id = 123
        
        # 模拟Essay.create方法
        with patch('app.models.essay.Essay.create', return_value=mock_essay):
            # 准备文件数据
            test_file = FileStorage(
                stream=BytesIO(b"This is a test file content"),
                filename="test.txt",
                content_type="text/plain"
            )
            
            # 构建表单数据
            data = {
                'title': '测试文件',
                'file': test_file,
                'grade': 'junior'
            }
            
            # 发送上传请求
            response = self.client.post(
                '/api/v1/correction/upload',
                data=data,
                content_type='multipart/form-data'
            )
            
            # 验证上传响应
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.data)
            self.assertTrue(response_data['success'])
            
            # 验证请求了批改
            mock_corrector_instance.correct_essay.assert_called_once()
            
            # 模拟获取批改结果的请求
            with patch('app.models.essay.Essay.find_by_id', return_value=mock_essay):
                # 获取批改结果
                response = self.client.get(f'/api/v1/correction/essays/{mock_essay.id}')
                
                # 验证批改结果响应
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                self.assertTrue(response_data['success'])
                self.assertIn('essay', response_data)

class TestFileProcessingComponents(unittest.TestCase):
    """测试文件处理组件的集成"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.upload_dir = tempfile.mkdtemp()
        
        # 清除单例状态
        FileService._instance = None
        
        # 配置服务
        with patch('app.config.config.APP_CONFIG', {'UPLOAD_FOLDER': self.upload_dir}):
            with patch('app.config.config.AI_CONFIG', {'QWEN_API_KEY': 'test_key'}):
                self.file_service = FileService()
                self.file_service.upload_folder = self.upload_dir
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试文件
        for root, dirs, files in os.walk(self.upload_dir):
            for file in files:
                os.unlink(os.path.join(root, file))
        
        # 移除测试目录
        os.rmdir(self.upload_dir)
    
    def test_text_file_processing_integration(self):
        """测试文本文件处理的集成"""
        # 创建测试文本文件
        test_content = "这是测试文本内容，用于集成测试。"
        test_file_path = os.path.join(self.upload_dir, "test.txt")
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # 直接使用文件服务处理文件
        try:
            content = self.file_service.extract_text_from_file(test_file_path)
            
            # 验证文本提取结果
            self.assertEqual(content, test_content)
        except ImportError:
            self.skipTest("缺少必要的依赖库")
        except Exception as e:
            self.fail(f"文件处理失败: {str(e)}")
    
    @unittest.skip("需要DOCX处理库")
    def test_docx_file_processing_integration(self):
        """测试DOCX文件处理的集成"""
        # 此测试需要实际的DOCX文件和相关库
        # 如果环境中没有这些依赖，可以跳过此测试
        test_file_path = os.path.join(self.upload_dir, "test.docx")
        
        # 这里需要一个真实的DOCX文件
        # 为了测试的一致性，通常会使用预先准备好的测试文件
        
        try:
            content = self.file_service.extract_text_from_file(test_file_path)
            self.assertIsNotNone(content)
            self.assertGreater(len(content), 0)
        except ImportError:
            self.skipTest("缺少DOCX处理库")
        except FileNotFoundError:
            self.skipTest("缺少测试DOCX文件")
        except Exception as e:
            self.fail(f"DOCX处理失败: {str(e)}")
    
    @unittest.skip("需要PDF处理库")
    def test_pdf_file_processing_integration(self):
        """测试PDF文件处理的集成"""
        # 此测试需要实际的PDF文件和相关库
        test_file_path = os.path.join(self.upload_dir, "test.pdf")
        
        # 这里需要一个真实的PDF文件
        
        try:
            content = self.file_service.extract_text_from_file(test_file_path)
            self.assertIsNotNone(content)
            self.assertGreater(len(content), 0)
        except ImportError:
            self.skipTest("缺少PDF处理库")
        except FileNotFoundError:
            self.skipTest("缺少测试PDF文件")
        except Exception as e:
            self.fail(f"PDF处理失败: {str(e)}")

if __name__ == '__main__':
    unittest.main() 