#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改API路由模块
提供作文批改相关的API接口
"""

import logging
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename
import os

from app.core.correction.correction_service import CorrectionService
from app.api.middleware.auth import token_required
from app.utils import FileHandler

# 创建蓝图
essays_bp = Blueprint('essays', __name__)
logger = logging.getLogger(__name__)

# 初始化服务
correction_service = CorrectionService()
file_handler = FileHandler()

@essays_bp.route('', methods=['POST'])
@token_required
def submit_essay():
    """
    提交作文API
    
    提交作文内容进行批改
    
    请求体:
        title: 作文标题
        content: 作文内容
    
    返回:
        作文提交结果
    """
    try:
        # 获取JSON数据
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '无效的请求数据'
            }), 400
        
        # 获取作文信息
        title = data.get('title')
        content = data.get('content')
        
        # 检查必填字段
        if not title or not content:
            return jsonify({
                'status': 'error',
                'message': '标题和内容不能为空'
            }), 400
        
        # 调用服务提交作文
        user_id = g.user.get('id')
        result = correction_service.submit_essay(user_id, title, content)
        
        # 处理结果
        if result.get('status') == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"提交作文时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@essays_bp.route('/file', methods=['POST'])
@token_required
def submit_essay_file():
    """
    上传作文文件API
    
    上传作文文件进行批改
    
    请求体:
        title: 作文标题
        file: 作文文件（支持文本文件和图片文件）
    
    返回:
        作文提交结果
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': '没有上传文件'
            }), 400
        
        # 获取文件和标题
        file = request.files['file']
        title = request.form.get('title')
        
        # 检查文件名和标题
        if file.filename == '' or not title:
            return jsonify({
                'status': 'error',
                'message': '文件名和标题不能为空'
            }), 400
        
        # 调用服务提交作文文件
        user_id = g.user.get('id')
        result = correction_service.submit_essay_file(user_id, title, file, file.filename)
        
        # 处理结果
        if result.get('status') == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"提交作文文件时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@essays_bp.route('/<int:essay_id>', methods=['GET'])
@token_required
def get_essay(essay_id):
    """
    获取作文API
    
    获取作文批改详细信息
    
    参数:
        essay_id: 作文ID
    
    返回:
        作文及批改详情
    """
    try:
        # 调用服务获取作文信息
        user_id = g.user.get('id')
        result = correction_service.get_essay(essay_id, user_id)
        
        # 处理结果
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 404
        
    except Exception as e:
        logger.error(f"获取作文信息时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@essays_bp.route('', methods=['GET'])
@token_required
def get_user_essays():
    """
    获取用户作文列表API
    
    获取当前用户的作文列表
    
    查询参数:
        page: 页码（默认1）
        per_page: 每页数量（默认10）
        status: 作文状态过滤
    
    返回:
        作文列表及分页信息
    """
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        # 检查页码和每页数量
        if page < 1 or per_page < 1 or per_page > 100:
            return jsonify({
                'status': 'error',
                'message': '无效的分页参数'
            }), 400
        
        # 调用服务获取作文列表
        user_id = g.user.get('id')
        result = correction_service.get_user_essays(user_id, page, per_page, status)
        
        # 处理结果
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"获取用户作文列表时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@essays_bp.route('/<int:essay_id>', methods=['DELETE'])
@token_required
def delete_essay(essay_id):
    """
    删除作文API
    
    删除指定的作文
    
    参数:
        essay_id: 作文ID
    
    返回:
        删除结果
    """
    try:
        # 调用服务删除作文
        user_id = g.user.get('id')
        result = correction_service.delete_essay(essay_id, user_id)
        
        # 处理结果
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"删除作文时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500

@essays_bp.route('/file-types', methods=['GET'])
@token_required
def get_supported_file_types():
    """
    获取支持的文件类型API
    
    获取系统支持的作文文件类型
    
    返回:
        支持的文件类型列表
    """
    try:
        # 调用服务获取支持的文件类型
        result = correction_service.get_supported_file_types()
        
        # 处理结果
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"获取支持的文件类型时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500 