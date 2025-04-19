#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文档处理模块
用于处理各种格式的文档并提取文本内容
"""

import os
import logging
import tempfile
from werkzeug.utils import secure_filename
import docx
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import subprocess
import platform
import time

# 配置日志
logger = logging.getLogger(__name__)

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    'txt': 'text/plain',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif'
}

def allowed_file(filename):
    """
    检查文件是否为允许的类型
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 文件类型是否允许
    """
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    # 确保使用字典的keys方法检查扩展名
    return ext in ALLOWED_EXTENSIONS.keys()

def extract_text_from_txt(file_path):
    """
    从txt文件中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except UnicodeDecodeError:
            logger.error(f"无法读取文件: {file_path}")
            raise Exception("无法读取文件，请确保文件编码正确")

def extract_text_from_docx(file_path):
    """
    从docx文件中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本内容
    """
    try:
        doc = docx.Document(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        logger.error(f"处理DOCX文件时出错: {e}")
        raise Exception("无法读取DOCX文件")

def extract_text_from_doc(file_path):
    """
    从doc文件中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本内容
    """
    try:
        # 首先尝试使用python-docx直接读取
        try:
            return extract_text_from_docx(file_path)
        except Exception as docx_error:
            logger.warning(f"使用python-docx读取DOC文件失败: {docx_error}")
        
        # 然后尝试使用pandoc
        try:
            if platform.system() == 'Windows':
                output_path = file_path + '.docx'
                subprocess.run(['pandoc', '-f', 'doc', '-t', 'docx', '-o', output_path, file_path], check=True)
                text = extract_text_from_docx(output_path)
                try:
                    os.unlink(output_path)
                except:
                    pass
                return text
            else:
                # 在Linux/Mac上使用antiword
                result = subprocess.run(['antiword', file_path], capture_output=True, text=True, check=True)
                return result.stdout
        except Exception as pandoc_error:
            logger.warning(f"使用pandoc转换DOC文件失败: {pandoc_error}")
            
        # 最后尝试使用其他方法
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.visible = False
            doc = word.Documents.Open(file_path)
            text = doc.Content.Text
            doc.Close()
            word.Quit()
            return text
        except Exception as com_error:
            logger.warning(f"使用COM接口读取DOC文件失败: {com_error}")
            
        raise Exception("所有读取方法都失败")
    except Exception as e:
        logger.error(f"处理DOC文件时出错: {e}")
        raise Exception("无法读取DOC文件，请转换为DOCX格式后重试")

def extract_text_from_pdf(file_path):
    """
    从PDF文件中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本内容
    """
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        logger.error(f"处理PDF文件时出错: {e}")
        raise Exception("无法读取PDF文件")

def extract_text_from_image(file_path):
    """
    从图片中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本内容
    """
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='chi_sim')
        return text
    except Exception as e:
        logger.error(f"处理图片文件时出错: {e}")
        raise Exception("无法从图片中提取文本")

def process_document(file):
    """
    处理上传的文档文件，提取文本内容
    
    Args:
        file: 上传的文件对象
        
    Returns:
        tuple: (文本内容, 文件标题)
    """
    temp_file = None
    try:
        # 安全检查
        if not file or not hasattr(file, 'filename') or file.filename == '':
            raise ValueError("未选择文件或文件对象无效")
        
        # 首先保存原始文件名，并提取扩展名
        original_filename = file.filename
        if '.' not in original_filename:
            logger.error(f"文件没有扩展名: {original_filename}")
            raise ValueError(f"文件没有扩展名: {original_filename}")
            
        # 提取原始扩展名 (在应用secure_filename前)
        original_ext = original_filename.rsplit('.', 1)[1].lower()
        
        # 检查扩展名是否允许
        if original_ext not in ALLOWED_EXTENSIONS:
            logger.error(f"不支持的文件格式: .{original_ext}")
            raise ValueError(f"不支持的文件格式: .{original_ext}")
            
        # 安全处理文件名 (可能会删除中文字符)
        safe_filename = secure_filename(original_filename)
        
        # 确保安全文件名仍有扩展名
        if '.' not in safe_filename:
            safe_filename = f"file_{int(time.time())}.{original_ext}"
            
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, safe_filename)
        
        # 保存上传的文件
        file.save(temp_file)
        
        # 记录文件处理信息
        logger.info(f"原始文件名: {original_filename}, 安全文件名: {safe_filename}, 扩展名: .{original_ext}")
        logger.info(f"临时文件路径: {temp_file}")
        
        # 根据文件类型提取文本
        content = None
        if original_ext == 'txt':
            content = extract_text_from_txt(temp_file)
            logger.info(f"成功从.txt文件提取文本，长度: {len(content)}")
        elif original_ext == 'docx':
            content = extract_text_from_docx(temp_file)
            logger.info(f"成功从.docx文件提取文本，长度: {len(content)}")
        elif original_ext == 'doc':
            content = extract_text_from_doc(temp_file)
            logger.info(f"成功从.doc文件提取文本，长度: {len(content)}")
        elif original_ext == 'pdf':
            content = extract_text_from_pdf(temp_file)
            logger.info(f"成功从.pdf文件提取文本，长度: {len(content)}")
        elif original_ext in ['jpg', 'jpeg', 'png', 'gif']:
            content = extract_text_from_image(temp_file)
            logger.info(f"成功从图片文件提取文本，长度: {len(content)}")
            
        if not content:
            raise ValueError("文件内容为空")
            
        # 从原始文件名中提取标题 (保留中文字符)
        title = os.path.splitext(original_filename)[0]
        
        return content.strip(), title
        
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        raise
        
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.debug(f"临时文件已清理: {temp_file}")
            except Exception as e:
                logger.error(f"清理临时文件失败: {str(e)}") 