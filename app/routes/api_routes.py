#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.essay import Essay, Correction
from app.models.task import Task

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/tasks/status', methods=['POST'])
@login_required
def check_tasks_status():
    """
    检查任务状态API
    接收任务ID列表，返回每个任务的最新状态
    """
    try:
        data = request.get_json()
        if not data or 'task_ids' not in data:
            return jsonify({'success': False, 'message': '请求参数错误'}), 400
            
        task_ids = data['task_ids']
        if not isinstance(task_ids, list):
            return jsonify({'success': False, 'message': '任务ID必须是列表'}), 400
            
        # 获取任务状态
        tasks_info = []
        
        for task_id in task_ids:
            if not task_id:
                continue
                
            # 尝试找到相关的任务
            task = Task.query.filter_by(id=task_id).first()
            if task:
                task_info = {
                    'id': task_id,
                    'status': task.status,
                    'error': task.error
                }
            else:
                # 如果任务表中没有找到，尝试通过Essay表查找
                essay = Essay.query.filter_by(task_id=task_id).first()
                if essay:
                    if essay.status == 'COMPLETED':
                        status = 'SUCCESS'
                    elif essay.status == 'ERROR':
                        status = 'FAILURE'
                    elif essay.status == 'CORRECTING':
                        status = 'STARTED'
                    else:
                        status = 'PENDING'
                        
                    # 检查是否有错误信息
                    error = None
                    correction = Correction.query.filter_by(essay_id=essay.id).order_by(Correction.created_at.desc()).first()
                    if correction and correction.error:
                        error = correction.error
                        
                    task_info = {
                        'id': task_id,
                        'status': status,
                        'error': error
                    }
                else:
                    # 找不到任务，标记为FAILURE
                    task_info = {
                        'id': task_id,
                        'status': 'FAILURE',
                        'error': '找不到任务信息'
                    }
                    
            tasks_info.append(task_info)
            
        return jsonify({
            'success': True,
            'tasks': tasks_info
        })
        
    except Exception as e:
        current_app.logger.error(f"检查任务状态时出错: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'服务器错误: {str(e)}'
        }), 500 