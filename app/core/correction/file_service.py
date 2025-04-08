#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件服务模块
负责处理作文文件的上传、处理和存储，支持文本文件和图片识别
"""

import os
import uuid
import logging
import tempfile
import base64
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union
from werkzeug.utils import secure_filename

from app.utils.exceptions import FileProcessError
from app.config import config

# 配置日志记录器
logger = logging.getLogger('app.core.correction.file')

class FileService:
    """
    文件服务类
    
    负责处理作文相关的文件操作：
    1. 文件上传和保存
    2. 文件格式转换和提取文本
    3. 图片识别处理
    4. 文件管理和清理
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(FileService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化文件服务"""
        if self._initialized:
            return
            
        # 初始化上传目录
        self.upload_folder = config.APP_CONFIG.get('UPLOAD_FOLDER', 'uploads/essays')
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # 允许的文件类型
        self.allowed_extensions = set(['txt', 'docx', 'pdf', 'jpg', 'jpeg', 'png'])
        
        # 千问视觉模型配置
        self.qwen_api_key = config.AI_CONFIG.get('QWEN_API_KEY', '')
        self.qwen_api_url = config.AI_CONFIG.get('QWEN_API_URL', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation')
        self.qwen_model = config.AI_CONFIG.get('QWEN_MODEL', 'qwen-vl-plus-latest')
        
        self._initialized = True
        
    def process_uploaded_file(self, file, title: Optional[str] = None) -> Dict[str, Any]:
        """
        处理上传的文件
        
        Args:
            file: 上传的文件对象
            title: 可选的文件标题，默认使用文件名
            
        Returns:
            Dict: 包含文件处理结果的字典
            
        Raises:
            FileProcessError: 如果文件处理失败
        """
        if not file or file.filename == '':
            raise FileProcessError("未选择文件")
            
        # 检查文件类型
        if not self.allowed_file(file.filename):
            raise FileProcessError(f"不支持的文件类型，请上传 {', '.join(self.allowed_extensions)} 格式的文件")
        
        try:
            # 生成安全的文件名
            filename = self.generate_secure_filename(file.filename)
            
            # 保存文件
            file_path = os.path.join(self.upload_folder, filename)
            file.save(file_path)
            
            # 提取内容
            content = self.extract_text_from_file(file_path)
            
            # 生成标题（如果未提供）
            if not title:
                title = os.path.splitext(os.path.basename(file.filename))[0]
                
            return {
                "success": True,
                "filename": filename,
                "file_path": file_path,
                "title": title,
                "content": content,
                "word_count": len(content)
            }
            
        except Exception as e:
            logger.error(f"文件处理异常: {str(e)}", exc_info=True)
            raise FileProcessError(f"文件处理失败: {str(e)}")
    
    def allowed_file(self, filename: str) -> bool:
        """
        检查文件是否为允许的类型
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 如果文件类型允许则返回True
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def generate_secure_filename(self, original_filename: str) -> str:
        """
        生成安全的文件名
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            str: 安全的文件名
        """
        # 获取文件扩展名
        ext = os.path.splitext(original_filename)[1].lower()
        
        # 生成唯一标识符
        unique_id = uuid.uuid4().hex[:8]
        
        # 使用时间戳和UUID生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # 安全处理原文件名
        base_name = secure_filename(os.path.splitext(original_filename)[0])
        if len(base_name) > 20:  # 限制基本名称长度
            base_name = base_name[:20]
            
        return f"{timestamp}_{unique_id}_{base_name}{ext}"
    
    def extract_text_from_file(self, file_path: str) -> str:
        """
        从文件中提取文本内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 提取的文本内容
            
        Raises:
            FileProcessError: 如果文本提取失败
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            # TXT文件处理
            if file_ext == '.txt':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except UnicodeDecodeError:
                    # 尝试GBK编码
                    with open(file_path, 'r', encoding='gbk') as f:
                        return f.read()
            
            # DOCX文件处理
            elif file_ext == '.docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    return '\n'.join([para.text for para in doc.paragraphs])
                except ImportError:
                    logger.error("docx模块未安装，无法处理DOCX文件")
                    raise FileProcessError("系统未配置DOCX处理功能，请上传TXT格式文件")
            
            # PDF文件处理
            elif file_ext == '.pdf':
                try:
                    import PyPDF2
                    text = []
                    with open(file_path, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        for page_num in range(len(reader.pages)):
                            text.append(reader.pages[page_num].extract_text())
                    return '\n'.join(text)
                except ImportError:
                    logger.error("PyPDF2模块未安装，无法处理PDF文件")
                    raise FileProcessError("系统未配置PDF处理功能，请上传TXT格式文件")
            
            # 图片文件处理 (使用千问视觉模型)
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                if not self.qwen_api_key:
                    raise FileProcessError("系统未配置图片识别功能，请上传文本格式文件")
                
                # 调用千问API进行图片内容识别
                content = self._extract_text_from_image(file_path)
                if not content:
                    raise FileProcessError("无法从图片中提取文本内容")
                
                return content
            
            # 其他不支持的文件类型
            else:
                raise FileProcessError(f"不支持的文件类型: {file_ext}")
                
        except Exception as e:
            logger.error(f"文本提取失败: {str(e)}", exc_info=True)
            raise FileProcessError(f"无法从文件中提取文本: {str(e)}")
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """
        使用千问视觉模型从图片中提取文本
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            str: 识别的文本内容
            
        Raises:
            FileProcessError: 如果图片识别失败
        """
        try:
            # 读取图片文件并转换为Base64
            with open(image_path, 'rb') as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            # 构建API请求
            headers = {
                'Authorization': f'Bearer {self.qwen_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.qwen_model,
                'input': {
                    'messages': [
                        {
                            'role': 'system',
                            'content': '你是一个文字识别助手，请提取图片中的所有文本内容，只返回纯文本不要加任何解释'
                        },
                        {
                            'role': 'user',
                            'content': [
                                {'image': base64_image},
                                {'text': '请帮我提取这张图片中的所有文字内容，不需要任何说明，只需要原始文本'}
                            ]
                        }
                    ]
                },
                'parameters': {
                    'result_format': 'message'
                }
            }
            
            # 发送请求
            response = requests.post(
                self.qwen_api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # 检查响应状态
            response.raise_for_status()
            result = response.json()
            
            # 提取文本内容
            content = result.get('output', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # 日志记录识别结果
            logger.info(f"图片识别成功，提取文本长度: {len(content)} 字符")
            
            return content
            
        except requests.RequestException as e:
            logger.error(f"千问API请求失败: {str(e)}", exc_info=True)
            raise FileProcessError(f"图片识别服务请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"图片识别处理异常: {str(e)}", exc_info=True)
            raise FileProcessError(f"图片识别失败: {str(e)}")
    
    def delete_file(self, filename: str) -> bool:
        """
        删除文件
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 如果删除成功则返回True
        """
        file_path = os.path.join(self.upload_folder, filename)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"文件已删除: {filename}")
                return True
            else:
                logger.warning(f"尝试删除不存在的文件: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"文件删除失败: {str(e)}", exc_info=True)
            return False
