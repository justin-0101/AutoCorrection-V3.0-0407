#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改API路由
提供与作文批改相关的HTTP API端点
"""

import os
import logging
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename

from app.core.correction import CorrectionService, FileService, AnalysisService
from app.core.auth import login_required, admin_required
from app.utils.api_decorators import api_error_handler

# 创建蓝图
correction_bp = Blueprint('correction', __name__)

# 配置日志记录器
logger = logging.getLogger('app.api.correction')

@correction_bp.route('/essays', methods=['POST'])
@login_required
@api_error_handler
def submit_essay():
    """
    提交作文进行批改
    
    请求体:
        {
            "title": "作文标题",
            "content": "作文内容",
            "grade": "年级水平" // primary, junior, senior, college
        }
        
    返回:
        {
            "success": true/false,
            "message": "描述信息",
            "essay_id": 123  // 如果成功
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 解析请求数据
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "无效的请求数据"}), 400
    
    title = data.get('title', '')
    content = data.get('content', '')
    grade = data.get('grade', 'junior')  # 默认为初中水平
    
    if not content:
        return jsonify({"success": False, "message": "作文内容不能为空"}), 400
        
    # 提交作文批改
    correction_service = CorrectionService()
    result = correction_service.submit_essay(
        user_id=user.id,
        title=title,
        content=content,
        grade=grade
    )
    
    if result.get('status') == 'success':
        return jsonify({
            "success": True,
            "message": result.get('message', '作文已提交并开始批改'),
            "essay_id": result.get('essay_id')
        }), 201
    else:
        return jsonify({
            "success": False,
            "message": result.get('message', '提交失败')
        }), 400

@correction_bp.route('/essays/file', methods=['POST'])
@login_required
@api_error_handler
def submit_essay_file():
    """
    上传文件提交作文进行批改
    
    请求体:
        - file: 文件对象
        - title: 作文标题 (可选)
        - grade: 年级水平 (可选，默认为junior)
        
    返回:
        {
            "success": true/false,
            "message": "描述信息",
            "essay_id": 123,  // 如果成功
            "word_count": 500,  // 如果成功
            "source_type": "upload"  // 来源类型
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 获取参数
    title = request.form.get('title', '')
    grade = request.form.get('grade', 'junior')
    
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "未找到上传的文件"
            }), 400
            
        file = request.files['file']
        if not file:
            return jsonify({
                "success": False,
                "message": "请选择要上传的文件"
            }), 400
            
        # 处理文件
        file_service = FileService()
        file_result = file_service.process_uploaded_file(file)
        
        if not file_result.get('success'):
            return jsonify({
                "success": False,
                "message": file_result.get('message', '文件处理失败')
            }), 400
            
        # 使用作文标题
        title = title or file_result.get('title', '')
        
        # 提交作文批改
        correction_service = CorrectionService()
        result = correction_service.submit_essay(
            user_id=user.id,
            title=title,
            content=file_result['content'],
            grade=grade
        )
        
        if result.get('status') == 'success':
            return jsonify({
                "success": True,
                "message": "作文已提交并开始批改",
                "essay_id": result['essay_id'],
                "word_count": file_result.get('word_count', 0),
                "source_type": "upload",
                "task_id": result.get('task_id')
            }), 201
        else:
            # 删除文件
            file_service.delete_file(file_result.get('filename'))
            return jsonify({
                "success": False,
                "message": result.get('message', '提交失败')
            }), 400
            
    except Exception as e:
        logger.error(f"文件上传处理错误: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"文件处理错误: {str(e)}"
        }), 500

@correction_bp.route('/essays/<int:essay_id>', methods=['GET'])
@login_required
@api_error_handler
def get_essay(essay_id):
    """
    获取作文及批改结果
    
    URL参数:
        - essay_id: 作文ID
        
    返回:
        {
            "success": true/false,
            "essay": {
                "id": 123,
                "title": "作文标题",
                "content": "作文内容",
                "score": 85,
                "feedback": {...},
                ...
            }
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 获取作文批改结果
    result = CorrectionService().get_correction_result(essay_id, user.id)
    
    if result.get("success", False):
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@correction_bp.route('/essays/status/<int:essay_id>', methods=['GET'])
@login_required
@api_error_handler
def get_essay_status(essay_id):
    """
    获取作文批改状态
    
    URL参数:
        - essay_id: 作文ID
        
    返回:
        {
            "success": true/false,
            "status": "pending/processing/completed/failed",
            "is_active": true/false,
            ...
        }
    """
    # 获取作文状态
    result = CorrectionService().get_correction_status(essay_id)
    
    if result.get("success", False):
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@correction_bp.route('/essays', methods=['GET'])
@login_required
@api_error_handler
def list_essays():
    """
    获取用户作文列表
    
    URL查询参数:
        - limit: 每页数量，默认20
        - offset: 分页偏移量，默认0
        
    返回:
        {
            "success": true/false,
            "essays": [
                {
                    "id": 123,
                    "title": "作文标题",
                    "score": 85,
                    "status": "completed",
                    ...
                },
                ...
            ],
            "total": 42,
            "limit": 20,
            "offset": 0
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 获取分页参数
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 获取作文列表
    result = CorrectionService().list_user_corrections(user.id, limit, offset)
    
    return jsonify(result), 200

@correction_bp.route('/analysis/progress', methods=['GET'])
@login_required
@api_error_handler
def get_progress_report():
    """
    获取用户作文进步报告
    
    URL查询参数:
        - period: 时间周期，可选值：week, month, year，默认month
        
    返回:
        {
            "success": true/false,
            "has_data": true/false,
            "period": "month",
            "data": [...],
            "progress": {...},
            "stats": {...}
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 获取时间周期参数
    period = request.args.get('period', 'month')
    
    # 获取进步报告
    result = AnalysisService().get_user_progress_report(user.id, period)
    
    return jsonify(result), 200

@correction_bp.route('/analysis/errors', methods=['GET'])
@login_required
@api_error_handler
def get_common_errors():
    """
    获取用户常见错误统计
    
    URL查询参数:
        - limit: 返回的错误数量限制，默认10
        
    返回:
        {
            "success": true/false,
            "has_data": true/false,
            "total_errors": 42,
            "unique_errors": 15,
            "common_errors": [...]
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 获取限制参数
    limit = request.args.get('limit', 10, type=int)
    
    # 获取常见错误统计
    result = AnalysisService().get_user_common_errors(user.id, limit)
    
    return jsonify(result), 200

@correction_bp.route('/analysis/suggestions', methods=['GET'])
@login_required
@api_error_handler
def get_suggestions():
    """
    获取用户改进建议
    
    返回:
        {
            "success": true/false,
            "has_suggestions": true/false,
            "suggestions": [...]
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 获取改进建议
    result = AnalysisService().get_improvement_suggestions(user.id)
    
    return jsonify(result), 200

@correction_bp.route('/analysis/performance', methods=['GET'])
@login_required
@api_error_handler
def get_performance():
    """
    获取用户按类别的表现分析
    
    URL查询参数:
        - category: 分类类型，例如：grade_level, category等，默认grade_level
        
    返回:
        {
            "success": true/false,
            "has_data": true/false,
            "category_type": "grade_level",
            "total_essays": 42,
            "categories": [...]
        }
    """
    # 获取当前用户
    user = g.current_user
    
    # 获取类别参数
    category = request.args.get('category', 'grade_level')
    
    # 获取表现分析
    result = AnalysisService().get_performance_by_category(user.id, category)
    
    return jsonify(result), 200
