"""
文件服务单元测试
测试文件上传和处理功能
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open

from app.core.correction.file_service import FileService
from app.utils.exceptions import FileProcessError

class TestFileService(unittest.TestCase):
    """测试文件服务"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录模拟上传文件夹
        self.temp_dir = tempfile.mkdtemp()
        
        # 清除单例状态
        FileService._instance = None
        
        # 配置服务使用临时目录
        with patch('app.config.config.APP_CONFIG', {'UPLOAD_FOLDER': self.temp_dir}):
            with patch('app.config.config.AI_CONFIG', {'QWEN_API_KEY': 'test_key'}):
                self.file_service = FileService()
                self.file_service.upload_folder = self.temp_dir
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时文件夹
        shutil.rmtree(self.temp_dir)
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        # 创建两个实例
        with patch('app.config.config.APP_CONFIG', {'UPLOAD_FOLDER': self.temp_dir}):
            with patch('app.config.config.AI_CONFIG', {'QWEN_API_KEY': 'test_key'}):
                service1 = FileService()
                service2 = FileService()
                
                # 验证是同一个实例
                self.assertIs(service1, service2)
    
    def test_allowed_file(self):
        """测试文件类型验证"""
        # 测试允许的文件类型
        self.assertTrue(self.file_service.allowed_file('test.txt'))
        self.assertTrue(self.file_service.allowed_file('test.docx'))
        self.assertTrue(self.file_service.allowed_file('test.pdf'))
        self.assertTrue(self.file_service.allowed_file('test.jpg'))
        self.assertTrue(self.file_service.allowed_file('test.jpeg'))
        self.assertTrue(self.file_service.allowed_file('test.png'))
        
        # 测试不允许的文件类型
        self.assertFalse(self.file_service.allowed_file('test.exe'))
        self.assertFalse(self.file_service.allowed_file('test.php'))
        self.assertFalse(self.file_service.allowed_file('test.js'))
        self.assertFalse(self.file_service.allowed_file('test'))  # 无扩展名
    
    def test_generate_secure_filename(self):
        """测试安全文件名生成"""
        # 测试文件名转换
        original_name = "测试 file(1).txt"
        secure_name = self.file_service.generate_secure_filename(original_name)
        
        # 验证安全文件名格式
        self.assertIn(".txt", secure_name)  # 保留扩展名
        self.assertNotIn(" ", secure_name)  # 空格被转换
        self.assertNotIn("(", secure_name)  # 特殊字符被转换
        self.assertNotIn(")", secure_name)  # 特殊字符被转换
        
        # 验证包含时间戳和唯一ID
        parts = secure_name.split('_')
        self.assertGreaterEqual(len(parts), 3)
        
        # 验证过长文件名被截断
        long_name = "a" * 50 + ".pdf"
        secure_long = self.file_service.generate_secure_filename(long_name)
        
        # 验证基础名称部分被限制长度
        base_name_part = secure_long.split('_')[-1].split('.')[0]
        self.assertLessEqual(len(base_name_part), 20)
    
    @patch('app.core.correction.file_service.open', new_callable=mock_open, read_data="测试文本内容")
    def test_extract_text_from_file_txt(self, mock_file):
        """测试从TXT文件提取文本"""
        # 创建临时TXT文件
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # 调用提取方法
        content = self.file_service.extract_text_from_file(file_path)
        
        # 验证提取结果
        self.assertEqual(content, "测试文本内容")
        mock_file.assert_called_once_with(file_path, 'r', encoding='utf-8')
    
    @patch('docx.Document')
    def test_extract_text_from_file_docx(self, mock_document):
        """测试从DOCX文件提取文本"""
        # 模拟Document类和段落
        mock_para1 = MagicMock()
        mock_para1.text = "第一段"
        mock_para2 = MagicMock()
        mock_para2.text = "第二段"
        
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_document.return_value = mock_doc
        
        # 创建临时DOCX文件路径
        file_path = os.path.join(self.temp_dir, "test.docx")
        
        # 调用提取方法
        content = self.file_service.extract_text_from_file(file_path)
        
        # 验证提取结果
        self.assertEqual(content, "第一段\n第二段")
        mock_document.assert_called_once_with(file_path)
    
    @patch('PyPDF2.PdfReader')
    def test_extract_text_from_file_pdf(self, mock_pdf_reader):
        """测试从PDF文件提取文本"""
        # 模拟PDF页面
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "第一页"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "第二页"
        
        # 模拟PDF阅读器
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        # 创建临时PDF文件路径
        file_path = os.path.join(self.temp_dir, "test.pdf")
        
        # 模拟文件打开
        with patch('builtins.open', mock_open()):
            # 调用提取方法
            content = self.file_service.extract_text_from_file(file_path)
            
            # 验证提取结果
            self.assertEqual(content, "第一页\n第二页")
    
    @patch('app.core.correction.file_service.base64.b64encode')
    @patch('app.core.correction.file_service.requests.post')
    def test_extract_text_from_image(self, mock_post, mock_b64encode):
        """测试从图片提取文本"""
        # 模拟base64编码
        mock_b64encode.return_value = b'testbase64data'
        
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'output': {
                'choices': [
                    {'message': {'content': '图片中的文字内容'}}
                ]
            }
        }
        mock_post.return_value = mock_response
        
        # 创建临时图片文件路径
        file_path = os.path.join(self.temp_dir, "test.jpg")
        
        # 模拟文件打开
        with patch('builtins.open', mock_open(read_data=b'imagebinarydata')):
            # 调用提取方法
            content = self.file_service._extract_text_from_image(file_path)
            
            # 验证提取结果
            self.assertEqual(content, '图片中的文字内容')
            mock_post.assert_called_once()
            mock_b64encode.assert_called_once_with(b'imagebinarydata')
    
    @patch('app.core.correction.file_service.os.path.splitext')
    def test_extract_text_from_file_unsupported(self, mock_splitext):
        """测试处理不支持的文件类型"""
        mock_splitext.return_value = ["test", ".xyz"]
        
        # 创建临时文件路径
        file_path = os.path.join(self.temp_dir, "test.xyz")
        
        # 调用提取方法，应该引发异常
        with self.assertRaises(FileProcessError):
            self.file_service.extract_text_from_file(file_path)
    
    @patch('app.core.correction.file_service.FileService.extract_text_from_file')
    def test_process_uploaded_file(self, mock_extract):
        """测试处理上传文件"""
        # 模拟文件提取结果
        mock_extract.return_value = "提取的文本内容"
        
        # 创建模拟文件对象
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.save = MagicMock()
        
        # 调用处理方法
        result = self.file_service.process_uploaded_file(mock_file, "测试标题")
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "测试标题")
        self.assertEqual(result["content"], "提取的文本内容")
        self.assertEqual(result["word_count"], len("提取的文本内容"))
        
        # 验证文件保存
        mock_file.save.assert_called_once()
        mock_extract.assert_called_once()
    
    def test_process_uploaded_file_no_file(self):
        """测试处理空文件"""
        # 调用处理方法，应该引发异常
        with self.assertRaises(FileProcessError):
            self.file_service.process_uploaded_file(None)
    
    def test_process_uploaded_file_empty_filename(self):
        """测试处理空文件名"""
        # 创建模拟文件对象
        mock_file = MagicMock()
        mock_file.filename = ""
        
        # 调用处理方法，应该引发异常
        with self.assertRaises(FileProcessError):
            self.file_service.process_uploaded_file(mock_file)
    
    def test_process_uploaded_file_invalid_extension(self):
        """测试处理不允许的文件类型"""
        # 创建模拟文件对象
        mock_file = MagicMock()
        mock_file.filename = "test.exe"
        
        # 调用处理方法，应该引发异常
        with self.assertRaises(FileProcessError) as context:
            self.file_service.process_uploaded_file(mock_file)
            
        # 验证异常信息
        self.assertIn("不支持的文件类型", str(context.exception))
    
    @patch('app.core.correction.file_service.FileService.extract_text_from_file')
    def test_process_uploaded_file_extraction_error(self, mock_extract):
        """测试文本提取错误"""
        # 模拟提取异常
        mock_extract.side_effect = Exception("提取错误")
        
        # 创建模拟文件对象
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.save = MagicMock()
        
        # 调用处理方法，应该引发异常
        with self.assertRaises(FileProcessError) as context:
            self.file_service.process_uploaded_file(mock_file)
            
        # 验证异常信息
        self.assertIn("提取错误", str(context.exception))

if __name__ == '__main__':
    unittest.main() 