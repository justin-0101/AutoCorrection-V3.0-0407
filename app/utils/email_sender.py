#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮件发送工具
提供邮件发送功能，支持HTML模板和附件
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate, formataddr
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any, List, Optional, Union

from app.config import config

# 获取日志记录器
logger = logging.getLogger(__name__)

# 配置Jinja2模板环境
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'email')
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=True
)

def send_email(
    recipient: Union[str, List[str]],
    subject: str,
    template: str = None,
    data: Dict[str, Any] = None,
    text_content: str = None,
    attachments: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    发送邮件
    
    Args:
        recipient: 收件人邮箱或邮箱列表
        subject: 邮件主题
        template: 模板名称（不包含扩展名）
        data: 模板数据
        text_content: 纯文本内容（如果不使用模板）
        attachments: 附件列表，每个附件为字典，包含文件名和文件内容
        
    Returns:
        Dict: 发送结果
    """
    try:
        # 读取邮件配置
        email_config = config.MAIL_CONFIG
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = formataddr((email_config.get('sender_name', ''), email_config.get('sender_email', '')))
        msg['Date'] = formatdate(localtime=True)
        
        # 设置收件人
        if isinstance(recipient, list):
            msg['To'] = ', '.join(recipient)
        else:
            msg['To'] = recipient
        
        # 设置邮件内容
        if template:
            # 使用模板生成HTML内容
            try:
                template_obj = jinja_env.get_template(f"{template}.html")
                html_content = template_obj.render(**(data or {}))
                msg.attach(MIMEText(html_content, 'html', 'utf-8'))
                
                # 尝试添加纯文本版本
                try:
                    text_template = jinja_env.get_template(f"{template}.txt")
                    plain_content = text_template.render(**(data or {}))
                    msg.attach(MIMEText(plain_content, 'plain', 'utf-8'))
                except:
                    # 如果纯文本模板不存在，则使用一个简单的纯文本内容
                    msg.attach(MIMEText("请使用支持HTML的邮件客户端查看此邮件。", 'plain', 'utf-8'))
            except Exception as e:
                logger.error(f"模板渲染失败: {str(e)}", exc_info=True)
                return {"status": "error", "message": f"模板渲染失败: {str(e)}"}
        elif text_content:
            # 使用纯文本内容
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        else:
            logger.error("发送邮件失败: 未提供内容")
            return {"status": "error", "message": "未提供邮件内容"}
        
        # 添加附件
        if attachments:
            for attachment in attachments:
                if 'filename' not in attachment or 'content' not in attachment:
                    continue
                
                attach_part = MIMEApplication(attachment['content'])
                attach_part.add_header(
                    'Content-Disposition', 
                    'attachment', 
                    filename=attachment['filename']
                )
                msg.attach(attach_part)
        
        # 发送邮件
        with smtplib.SMTP(email_config.get('smtp_server'), email_config.get('smtp_port')) as server:
            if email_config.get('use_tls'):
                server.starttls()
            
            server.login(email_config.get('username'), email_config.get('password'))
            
            if isinstance(recipient, list):
                server.sendmail(email_config.get('sender_email'), recipient, msg.as_string())
            else:
                server.sendmail(email_config.get('sender_email'), [recipient], msg.as_string())
        
        logger.info(f"邮件发送成功，收件人: {recipient}, 主题: {subject}")
        
        return {
            "status": "success",
            "message": "邮件发送成功",
            "recipient": recipient,
            "subject": subject
        }
    
    except Exception as e:
        logger.error(f"邮件发送失败: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"邮件发送失败: {str(e)}"
        }


def send_simple_email(recipient: Union[str, List[str]], subject: str, content: str) -> Dict[str, Any]:
    """
    发送简单纯文本邮件
    
    Args:
        recipient: 收件人邮箱或邮箱列表
        subject: 邮件主题
        content: 邮件内容
        
    Returns:
        Dict: 发送结果
    """
    return send_email(
        recipient=recipient,
        subject=subject,
        text_content=content
    )


def send_template_email(recipient: Union[str, List[str]], subject: str, template: str,
                      data: Dict[str, Any]) -> Dict[str, Any]:
    """
    发送模板邮件
    
    Args:
        recipient: 收件人邮箱或邮箱列表
        subject: 邮件主题
        template: 模板名称
        data: 模板数据
        
    Returns:
        Dict: 发送结果
    """
    return send_email(
        recipient=recipient,
        subject=subject,
        template=template,
        data=data
    ) 