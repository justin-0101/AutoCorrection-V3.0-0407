#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件处理工具模块
处理文件上传、解析和保存相关功能
"""

import os
import io
import uuid
import logging
import mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

# 图像处理库
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Docx处理库
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# PDF处理库
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    try:
        import fitz  # PyMuPDF
        HAS_PYMUPDF = True
    except ImportError:
        HAS_PDF = False
        HAS_PYMUPDF = False

from app.config import config
from app.core.ai import AIClientFactory

logger = logging.getLogger(__name__)

class FileHandler:
    """文件处理工具类，支持各种文件格式的处理"""
    
    def __init__(self):
        """初始化文件处理工具"""
        self.allowed_extensions = config.APP_CONFIG.get('allowed_extensions', {})
        self.upload_folder = config.APP_CONFIG.get('upload_folder', 'uploads')
        self.max_content_length = config.APP_CONFIG.get('max_content_length', 16 * 1024 * 1024)
        
        # 确保上传目录存在
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # 初始化AI客户端
        ai_factory = AIClientFactory()
        self.ai_client = ai_factory.get_client()
    
    def allowed_file(self, filename):
        """
        检查文件扩展名是否允许
        
        Args:
            filename: 文件名
        
        Returns:
            tuple: (是否允许, 文件类型)
        """
        if not filename:
            return False, None
        
        # 获取扩展名（不带点）
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # 检查是否为允许的文本文件
        if ext in self.allowed_extensions.get('text', []):
            return True, 'text'
        
        # 检查是否为允许的图片文件
        if ext in self.allowed_extensions.get('image', []):
            return True, 'image'
        
        return False, None
    
    def process_file(self, file_data, filename, save_file=True):
        """
        处理上传的文件
        
        Args:
            file_data: 文件数据（字节流或FileStorage对象）
            filename: 原始文件名
            save_file: 是否保存文件
        
        Returns:
            dict: 处理结果
        """
        try:
            # 检查文件扩展名是否允许
            is_allowed, file_type = self.allowed_file(filename)
            if not is_allowed:
                logger.warning(f"不支持的文件类型: {filename}")
                return None
            
            # 确保文件名安全
            safe_filename = secure_filename(filename)
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"
            file_path = os.path.join(self.upload_folder, unique_filename)
            
            # 处理不同类型的输入
            if isinstance(file_data, FileStorage):
                content = file_data.read()
            else:
                content = file_data
            
            # 保存文件
            if save_file:
                with open(file_path, 'wb') as f:
                    f.write(content)
                logger.info(f"文件已保存: {file_path}")
            
            # 根据文件类型提取内容
            if file_type == 'text':
                text_content = self.extract_text_content(content, filename)
                mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                
                return {
                    'filename': unique_filename,
                    'original_filename': filename,
                    'path': file_path if save_file else None,
                    'content': text_content,
                    'mime_type': mime_type,
                    'size': len(content),
                    'source_type': 'text'
                }
            
            elif file_type == 'image':
                # 处理图片文件，使用AI服务提取内容
                text_content = self.extract_image_content(content, file_path if save_file else None)
                mime_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'
                
                return {
                    'filename': unique_filename,
                    'original_filename': filename,
                    'path': file_path if save_file else None,
                    'content': text_content,
                    'mime_type': mime_type,
                    'size': len(content),
                    'source_type': 'image'
                }
        
        except Exception as e:
            logger.error(f"处理文件时发生错误: {str(e)}", exc_info=True)
            return None
    
    def extract_text_content(self, content, filename):
        """
        从文本文件中提取内容
        
        Args:
            content: 文件内容（字节流）
            filename: 文件名
        
        Returns:
            str: 提取的文本内容
        """
        # 获取文件扩展名
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        try:
            # 处理TXT文件
            if ext == 'txt':
                # 尝试多种编码
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                for encoding in encodings:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                
                # 如果所有编码都失败，使用替换错误的方式解码
                return content.decode('utf-8', errors='replace')
            
            # 处理DOCX文件
            elif ext == 'docx' and HAS_DOCX:
                doc = docx.Document(io.BytesIO(content))
                return '\n'.join([para.text for para in doc.paragraphs])
            
            # 处理PDF文件
            elif ext == 'pdf':
                if HAS_PDF:
                    reader = PyPDF2.PdfReader(io.BytesIO(content))
                    return '\n'.join([page.extract_text() for page in reader.pages])
                elif HAS_PYMUPDF:
                    doc = fitz.open(stream=content, filetype="pdf")
                    return '\n'.join([page.get_text() for page in doc])
            
            # 不支持的格式或没有相应的库
            logger.warning(f"无法提取文本内容，不支持的文件格式或缺少相应的库: {filename}")
            return ""
        
        except Exception as e:
            logger.error(f"提取文本内容时发生错误: {str(e)}", exc_info=True)
            return ""
    
    def extract_image_content(self, content, file_path=None):
        """
        从图片文件中提取文本内容
        
        Args:
            content: 图片内容（字节流）
            file_path: 保存的文件路径（可选）
        
        Returns:
            str: 提取的文本内容
        """
        try:
            # 使用AI服务提取图片中的文本
            image_file = file_path if file_path and os.path.exists(file_path) else content
            
            # 调用AI客户端进行图片识别
            result = self.ai_client.recognize_image(image_file)
            
            if result and result.get('status') == 'success':
                return result.get('text', '')
            else:
                logger.warning(f"AI客户端提取图片内容失败: {result.get('message', '未知错误')}")
                return ""
        
        except Exception as e:
            logger.error(f"提取图片内容时发生错误: {str(e)}", exc_info=True)
            return ""
    
    def save_file(self, content, filename, subdirectory=None):
        """
        保存文件到指定目录
        
        Args:
            content: 文件内容（字节流）
            filename: 文件名
            subdirectory: 子目录（可选）
        
        Returns:
            str: 保存的文件路径
        """
        try:
            # 确保文件名安全
            safe_filename = secure_filename(filename)
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex}_{safe_filename}"
            
            # 确定保存路径
            save_path = self.upload_folder
            if subdirectory:
                save_path = os.path.join(save_path, subdirectory)
                os.makedirs(save_path, exist_ok=True)
            
            file_path = os.path.join(save_path, unique_filename)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"文件已保存: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"保存文件时发生错误: {str(e)}", exc_info=True)
            return None
    
    def delete_file(self, file_path):
        """
        删除文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            bool: 是否删除成功
        """
        try:
            if not file_path or not os.path.exists(file_path):
                return False
            
            os.remove(file_path)
            logger.info(f"文件已删除: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"删除文件时发生错误: {str(e)}", exc_info=True)
            return False
    
    def get_file_info(self, file_path):
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
        
        Returns:
            dict: 文件信息
        """
        try:
            if not file_path or not os.path.exists(file_path):
                return None
            
            file_stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            
            return {
                'filename': file_name,
                'path': file_path,
                'size': file_stat.st_size,
                'created_at': file_stat.st_ctime,
                'modified_at': file_stat.st_mtime,
                'mime_type': mime_type
            }
        
        except Exception as e:
            logger.error(f"获取文件信息时发生错误: {str(e)}", exc_info=True)
            return None 