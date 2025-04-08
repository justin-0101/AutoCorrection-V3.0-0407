#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改模块
用于处理用户提交的作文，进行批改、分析和存储结果

包含功能：
- 作文批改服务
- 作文分析服务
- 文件处理服务
"""

from app.core.correction.correction_service import CorrectionService
from app.core.correction.analysis_service import AnalysisService  
from app.core.correction.file_service import FileService

__all__ = [
    'CorrectionService',
    'AnalysisService',
    'FileService'
]
