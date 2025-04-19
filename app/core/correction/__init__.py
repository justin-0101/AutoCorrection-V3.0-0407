#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改服务模块
提供作文批改功能的各种组件
"""

from app.core.correction.correction_service import CorrectionService
from app.core.correction.ai_corrector import AICorrectionService
from app.core.correction.file_service import FileService
from app.core.correction.analysis_service import AnalysisService

# 尝试导入接口定义
try:
    from app.core.correction.interface import ICorrectionService, CorrectionResult
except ImportError:
    # 接口不存在时不进行任何操作
    pass

__all__ = [
    'CorrectionService',
    'AICorrectionService',
    'FileService',
    'AnalysisService'
]
