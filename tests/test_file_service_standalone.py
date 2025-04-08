#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件服务单元测试 - 独立版本
测试文件处理和内容提取
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open

# 定义一个简单的文件处理异常
class MockFileProcessError(Exception):
    """文件处理异常"""
    pass

# 模拟文件服务
class MockFileService:
    """
    模拟文件服务类
    提供文件上传处理和内容提取
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MockFileService, cls).__new__(cls)
            cls._instance.upload_folder = None
            cls._instance.allowed_extensions = {'txt', 'docx', 'pdf', 'jpg', 'jpeg', 'png'}
        return cls._instance
    
    def __init__(self):
        """初始化文件服务"""
        if not self.upload_folder:
            self.upload_folder = os.environ.get('UPLOAD_FOLDER', 'uploads')
            # 确保上传目录存在
            if not os.path.exists(self.upload_folder):
                os.makedirs(self.upload_folder, exist_ok=True)
    
    def allowed_file(self, filename):
        """
        检查文件类型是否允许
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 文件类型是否允许
        """
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def generate_secure_filename(self, filename):
        """
        生成安全的文件名
        添加时间戳和随机字符，避免文件名冲突
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 安全的文件名
        """
        import datetime
        import uuid
        
        # 获取当前时间戳
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        
        # 生成随机ID
        random_id = str(uuid.uuid4()).split('-')[0]
        
        # 获取原始扩展名
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # 获取基础文件名（不含扩展名）
        basename = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # 移除特殊字符
        basename = ''.join(c for c in basename if c.isalnum() or c in '_-')
        
        # 如果基础名称太长，截断它
        if len(basename) > 20:
            basename = basename[:20]
        
        # 组合新文件名
        secure_filename = f"{timestamp}_{random_id}_{basename}.{ext}"
        
        return secure_filename
    
    def extract_text_from_file(self, file_path):
        """
        从文件中提取文本
        支持txt, docx, pdf格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 提取的文本内容
            
        Raises:
            FileProcessError: 文件处理错误
        """
        # 获取文件扩展名
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()
        
        try:
            # 处理不同类型的文件
            if extension == '.txt':
                # 处理文本文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
            elif extension == '.docx':
                # 模拟DOCX处理
                return "这是从DOCX文件中提取的模拟文本内容"
                
            elif extension == '.pdf':
                # 模拟PDF处理
                return "这是从PDF文件中提取的模拟文本内容"
                
            elif extension in ['.jpg', '.jpeg', '.png']:
                # 模拟图片OCR处理
                return "这是从图片中识别的模拟文本内容"
                
            else:
                # 不支持的文件类型
                raise MockFileProcessError(f"不支持的文件类型: {extension}")
                
        except Exception as e:
            # 处理各种异常
            raise MockFileProcessError(f"提取文本失败: {str(e)}")
    
    def process_uploaded_file(self, file, title=None):
        """
        处理上传文件
        保存文件并提取文本内容
        
        Args:
            file: 上传的文件对象
            title: 文件标题(可选)
            
        Returns:
            dict: 处理结果
            
        Raises:
            FileProcessError: 文件处理错误
        """
        if not file:
            raise MockFileProcessError("未提供文件")
            
        if not file.filename:
            raise MockFileProcessError("文件名为空")
            
        if not self.allowed_file(file.filename):
            raise MockFileProcessError(f"不支持的文件类型: {file.filename}")
            
        try:
            # 生成安全的文件名
            filename = self.generate_secure_filename(file.filename)
            
            # 构建保存路径
            file_path = os.path.join(self.upload_folder, filename)
            
            # 保存文件
            file.save(file_path)
            
            # 提取文本内容
            content = self.extract_text_from_file(file_path)
            
            # 统计字数
            word_count = len(content)
            
            # 如果没有提供标题，使用文件名
            if not title:
                title = os.path.splitext(file.filename)[0]
                
            # 返回处理结果
            return {
                "success": True,
                "filename": filename,
                "file_path": file_path,
                "title": title,
                "content": content,
                "word_count": word_count
            }
            
        except Exception as e:
            # 处理异常
            raise MockFileProcessError(f"处理文件失败: {str(e)}")


# 测试文件服务
class TestFileService(unittest.TestCase):
    """测试文件服务"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录模拟上传文件夹
        self.temp_dir = tempfile.mkdtemp()
        
        # 重置单例状态
        MockFileService._instance = None
        
        # 设置环境变量
        self.original_env = os.environ.copy()
        os.environ['UPLOAD_FOLDER'] = self.temp_dir
        
        # 创建服务实例
        self.file_service = MockFileService()
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时文件夹
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # 恢复环境变量
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        # 创建两个实例
        service1 = MockFileService()
        service2 = MockFileService()
        
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
    
    @patch('builtins.open', new_callable=mock_open, read_data="测试文本内容")
    def test_extract_text_from_file_txt(self, mock_file):
        """测试从TXT文件提取文本"""
        # 创建测试文件路径
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # 调用提取方法
        content = self.file_service.extract_text_from_file(file_path)
        
        # 验证提取结果
        self.assertEqual(content, "测试文本内容")
        mock_file.assert_called_once_with(file_path, 'r', encoding='utf-8')
    
    def test_process_uploaded_file(self):
        """测试处理上传文件"""
        # 创建模拟文件对象
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.save = MagicMock()
        
        # 创建实际的临时文件用于内容提取
        tmp_file_path = os.path.join(self.temp_dir, "test.txt")
        with open(tmp_file_path, 'w', encoding='utf-8') as f:
            f.write("测试文本内容")
        
        # 模拟save方法的行为
        def save_effect(path):
            shutil.copy(tmp_file_path, path)
        
        mock_file.save.side_effect = save_effect
        
        # 调用处理方法
        with patch.object(self.file_service, 'extract_text_from_file', 
                          return_value="测试文本内容"):
            result = self.file_service.process_uploaded_file(mock_file, "测试标题")
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "测试标题")
        self.assertEqual(result["content"], "测试文本内容")
        self.assertEqual(result["word_count"], len("测试文本内容"))
        
        # 验证文件保存被调用
        mock_file.save.assert_called_once()
    
    def test_process_uploaded_file_no_file(self):
        """测试处理空文件"""
        # 调用处理方法，应该引发异常
        with self.assertRaises(MockFileProcessError):
            self.file_service.process_uploaded_file(None)
    
    def test_process_uploaded_file_invalid_extension(self):
        """测试处理不允许的文件类型"""
        # 创建模拟文件对象
        mock_file = MagicMock()
        mock_file.filename = "test.exe"
        
        # 调用处理方法，应该引发异常
        with self.assertRaises(MockFileProcessError) as context:
            self.file_service.process_uploaded_file(mock_file)
            
        # 验证异常信息
        self.assertIn("不支持的文件类型", str(context.exception))


if __name__ == "__main__":
    unittest.main() 