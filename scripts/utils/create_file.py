# 创建一个改进的文档处理模块
with open('utils/document_processor.py', 'w', encoding='utf-8') as f:
    f.write('''#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文档处理模块
用于处理各种格式的文档文件，支持 txt, docx, pdf 和图片格式
"""

import os
import logging
import tempfile
import traceback
from werkzeug.utils import secure_filename
from app.core.services.file_service import FileService

# 获取 logger
logger = logging.getLogger(__name__)

# 支持的文件类型
ALLOWED_EXTENSIONS = {
    'txt': '文本文件',
    'docx': 'Word文档',
    'pdf': 'PDF文档',
    'jpg': '图片',
    'jpeg': '图片',
    'png': '图片',
    'gif': '图片'
}

def allowed_file(filename):
    """
    检查文件是否为允许的类型
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 文件类型是否允许
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_docx(file_path):
    """
    从.docx 文件中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本
    """
    try:
        logger.info(f"处理.docx文件: {file_path}")
        
        # 使用 python-docx 库
        try:
            import docx
            doc = docx.Document(file_path)
            text = "\\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text])
            logger.info(f"成功从.docx文件提取文本，长度: {len(text)}")
            return text
        except ImportError:
            logger.warning("python-docx库未安装，使用替代方法")
            import zipfile
            from xml.etree.ElementTree import XML
            
            WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            PARA = WORD_NAMESPACE + 'p'
            TEXT = WORD_NAMESPACE + 't'
            
            with zipfile.ZipFile(file_path) as docx_zip:
                content = docx_zip.read('word/document.xml')
                tree = XML(content)
                
                paragraphs = []
                for paragraph in tree.iter(PARA):
                    texts = [node.text for node in paragraph.iter(TEXT) if node.text]
                    if texts:
                        paragraphs.append(''.join(texts))
                
                text = "\\n".join(paragraphs)
                logger.info(f"成功使用zipfile从.docx文件提取文本，长度: {len(text)}")
                return text
        
    except Exception as e:
        logger.error(f"处理.docx文件时出错: {str(e)}\\n{traceback.format_exc()}")
        raise Exception(f"无法读取.docx文件: {str(e)}")


def extract_text_from_txt(file_path):
    """
    从文本文件中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本
    """
    try:
        logger.info(f"处理.txt文件: {file_path}")
        
        # 尝试不同的编码方式
        encodings = ["utf-8", "gbk", "gb2312", "gb18030", "big5", "latin-1"]
        
        for encoding in encodings:
            try:
                file_service = FileService()
                with file_service.open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                logger.info(f"成功使用{encoding}编码读取文本文件，长度: {len(text)}")
                return text
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"使用{encoding}编码读取失败: {str(e)}")
        
        # 如果所有编码都失败，尝试二进制方式读取
        with file_service.open(file_path, 'rb') as f:
            binary_data = f.read()
        
        text = binary_data.decode('utf-8', errors='replace')
        logger.info(f"成功使用二进制方式读取文本文件，长度: {len(text)}")
        return text
        
    except Exception as e:
        logger.error(f"处理.txt文件时出错: {str(e)}\\n{traceback.format_exc()}")
        raise Exception(f"无法读取文本文件: {str(e)}")


def extract_text_from_pdf(file_path):
    """
    从PDF文件中提取文本
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本
    """
    try:
        logger.info(f"处理.pdf文件: {file_path}")
        
        try:
            import PyPDF2
            
            with file_service.open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\\n\\n"
                
                logger.info(f"成功从PDF文件提取文本，长度: {len(text)}")
                return text
                
        except ImportError:
            logger.warning("PyPDF2库未安装，尝试使用替代方法")
            
            try:
                from pdfminer.high_level import extract_text as pdf_extract_text
                text = pdf_extract_text(file_path)
                logger.info(f"成功使用pdfminer从PDF文件提取文本，长度: {len(text)}")
                return text
            except ImportError:
                raise Exception("未安装PDF处理库，请安装PyPDF2或pdfminer.six")
                
    except Exception as e:
        logger.error(f"处理PDF文件时出错: {str(e)}\\n{traceback.format_exc()}")
        raise Exception(f"无法读取PDF文件: {str(e)}")


def extract_text_from_image(file_path):
    """
    从图片中提取文本（OCR）
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 提取的文本
    """
    try:
        logger.info(f"处理图片文件: {file_path}")
        
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            
            logger.info(f"成功从图片提取文本，长度: {len(text)}")
            return text
            
        except ImportError:
            logger.warning("OCR库未安装")
            raise Exception("未安装OCR处理库，请安装pytesseract和Pillow")
            
    except Exception as e:
        logger.error(f"处理图片文件时出错: {str(e)}\\n{traceback.format_exc()}")
        raise Exception(f"无法处理图片文件: {str(e)}")


def process_document(file):
    """
    处理文档文件并提取文本
    
    Args:
        file: 文件对象 (Flask request.files 中的文件)
        
    Returns:
        tuple: (文本内容, 标题)
    """
    temp_file = None
    try:
        # 安全检查
        if not file or file.filename == '':
            raise Exception("未选择文件")
            
        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            raise Exception(f"不支持的文件格式。支持的格式：{', '.join(ALLOWED_EXTENSIONS.keys())}")
        
        # 创建临时文件并使用with语句确保正确关闭
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_file = temp.name
            file.save(temp_file)
        
        # 获取文件标题
        title = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
        
        logger.info(f"处理文件: {filename}，扩展名: {file_ext}")
        
        # 根据文件类型选择处理方法
        if file_ext == 'docx':
            content = extract_text_from_docx(temp_file)
        elif file_ext == 'txt':
            content = extract_text_from_txt(temp_file)
        elif file_ext == 'pdf':
            content = extract_text_from_pdf(temp_file)
        elif file_ext in ['jpg', 'jpeg', 'png', 'gif']:
            content = extract_text_from_image(temp_file)
        else:
            raise Exception(f"不支持的文件格式: {file_ext}")
        
        return content, title
        
    except Exception as e:
        logger.error(f"处理文档时出错: {str(e)}\\n{traceback.format_exc()}")
        raise Exception(f"处理文档时出错: {str(e)}")
        
    finally:
        # 确保总是清理临时文件
        try:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)
                logger.info(f"已删除临时文件: {temp_file}")
        except Exception as e:
            logger.error(f"清理临时文件时出错: {str(e)}")
'''.replace("\\n", "\n"))
    
print("改进版文档处理模块已创建！") 