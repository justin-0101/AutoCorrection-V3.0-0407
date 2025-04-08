#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改API路由模块
提供与作文批改相关的HTTP API端点
"""

import os
import time
import logging
import json
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename
import uuid

from core.correction_controller import correction_controller
from core.essay_model import Essay
from core.auth import login_required, get_current_user
from utils.exceptions import ValidationError, AIServiceError, api_error_handler

# 创建蓝图
correction_bp = Blueprint('correction_api', __name__)

# 配置日志记录器
logger = logging.getLogger('autocorrection.api')

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
    user = g.user
    
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
    success, message, essay_id = correction_controller.submit_correction(
        user_id=user.id,
        title=title,
        content=content,
        grade=grade
    )
    
    if success:
        return jsonify({
            "success": True,
            "message": message,
            "essay_id": essay_id
        }), 201
    else:
        return jsonify({
            "success": False,
            "message": message
        }), 400

@correction_bp.route('/essays/file', methods=['POST'])
@login_required
@api_error_handler
def submit_essay_file():
    """
    通过文件提交作文
    
    表单参数:
        - title: 作文标题
        - grade: 年级水平
        - file: 作文文件（txt或docx）
        
    返回:
        {
            "success": true/false,
            "message": "描述信息",
            "essay_id": 123  // 如果成功
        }
    """
    # 获取当前用户
    user = g.user
    
    # 验证文件上传
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "未找到上传文件"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "未选择文件"}), 400
        
    # 检查文件类型
    allowed_extensions = ['txt', 'docx']
    file_ext = os.path.splitext(file.filename)[1].lower()[1:]
    if file_ext not in allowed_extensions:
        return jsonify({
            "success": False, 
            "message": f"不支持的文件类型，请上传 {', '.join(allowed_extensions)} 格式的文件"
        }), 400
    
    # 获取其他表单参数
    title = request.form.get('title', os.path.splitext(file.filename)[0])
    grade = request.form.get('grade', 'junior')
    
    try:
        # 保存文件
        filename = secure_filename(f"{int(time.time())}_{str(uuid.uuid4())[:8]}_{file.filename}")
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # 读取文件内容
        content = ""
        if file_ext == 'txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
        elif file_ext == 'docx':
            import docx2txt
            content = docx2txt.process(file_path)
        
        if not content or len(content.strip()) < 50:
            return jsonify({
                "success": False, 
                "message": "文件内容为空或过短，请确保文件包含足够的文本内容"
            }), 400
            
        # 提交作文批改
        success, message, essay_id = correction_controller.submit_correction(
            user_id=user.id,
            title=title,
            content=content,
            grade=grade
        )
        
        if success:
            # 更新文件路径
            essay = Essay.find_by_id(essay_id)
            if essay:
                essay.file_path = filename
                essay.save()
                
            return jsonify({
                "success": True,
                "message": message,
                "essay_id": essay_id
            }), 201
        else:
            # 删除文件
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return jsonify({
                "success": False,
                "message": message
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
    user = g.user
    
    # 获取作文批改结果
    result = correction_controller.get_correction_result(essay_id, user.id)
    
    if result["success"]:
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
            "status": "pending/processing/completed/error",
            "is_active": true/false,
            ...
        }
    """
    # 获取作文状态
    result = correction_controller.get_correction_status(essay_id)
    
    if result["success"]:
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
    user = g.user
    
    # 获取分页参数
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 获取作文列表
    result = correction_controller.list_user_corrections(user.id, limit, offset)
    
    return jsonify(result), 200

def register_routes(app):
    """注册路由到Flask应用"""
    app.register_blueprint(correction_bp, url_prefix='/api/correction') 