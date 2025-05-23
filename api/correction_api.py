"""
作文批改API接口
提供作文批改和历史查询功能
"""

from flask import Blueprint, request, jsonify, current_app, g
import logging
from datetime import datetime
import time

from core.correction import correction_service
from app.models.essay import Essay
from app.models.user import User
from app.extensions import db
from utils.validators import validate_essay_submission
from tasks.correction_tasks import process_essay_correction

# 创建蓝图
correction_bp = Blueprint('correction', __name__, url_prefix='/api/correction')

# 获取logger
logger = logging.getLogger(__name__)

@correction_bp.route('/submit', methods=['POST'])
def submit_essay():
    """提交作文进行批改
    
    请求体:
    {
        "title": "作文标题",
        "content": "作文内容",
        "grade": "高中", // 可选
        "async": true    // 是否异步处理，默认为true
    }
    
    返回:
    {
        "status": "success",
        "data": {
            "essay_id": 1,
            "title": "作文标题",
            "status": "pending", // 异步模式下为pending/processing，同步模式下为completed
            "task_id": "xxxx-xxxx-xxxx", // 异步模式下的任务ID
            ... // 同步模式下返回完整结果
        }
    }
    """
    start_time = time.time()
    
    # 获取请求数据
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "未提供请求数据"
        }), 400
    
    # 获取作文数据
    title = data.get('title')
    content = data.get('content')
    grade = data.get('grade')  # 可选
    
    # 检查是否异步处理，默认为异步
    is_async = data.get('async', True)
    
    # 验证作文数据
    validation_result = validate_essay_submission(title, content)
    if not validation_result['valid']:
        return jsonify({
            "status": "error",
            "message": validation_result['message']
        }), 400
    
    # 获取用户ID（如果已登录）
    user_id = g.user.id if hasattr(g, 'user') and g.user.is_authenticated() else None
    
    try:
        # 创建作文记录
        essay = Essay(
            user_id=user_id if user_id else 0,  # 0表示匿名用户
            title=title,
            original_text=content,
            word_count=len(content.split()),
            grade=grade,
            status='pending',
            submission_time=datetime.utcnow()
        )
        
        # 保存到数据库
        db.session.add(essay)
        db.session.commit()
        
        # 记录创建时间
        creation_time = time.time() - start_time
        logger.info(f"创建作文记录完成，ID: {essay.id}, 耗时: {creation_time:.2f}秒")
        
        # 根据模式选择处理方式
        if is_async:
            # 异步模式：提交任务到队列
            task = process_essay_correction.delay(
                essay.id, title, content, user_id, grade
            )
            
            # 更新任务ID
            essay.task_id = task.id
            essay.status = 'processing'
            db.session.commit()
            
            logger.info(f"已提交异步批改任务，作文ID: {essay.id}, 任务ID: {task.id}")
            
            # 返回任务信息
            return jsonify({
                "status": "success",
                "data": {
                    "essay_id": essay.id,
                    "title": title,
                    "status": "processing",
                    "task_id": task.id,
                    "message": "作文已提交批改，正在异步处理中"
                }
            }), 202  # 202 Accepted
        else:
            # 同步模式：直接处理
            result = correction_service.correct_essay(
                essay_text=content,
                title=title,
                user_id=user_id,
                grade=grade,
                essay_id=essay.id
            )
            
            # 记录总处理时间
            total_time = time.time() - start_time
            logger.info(f"同步作文批改完成，总耗时: {total_time:.2f}秒")
            
            # 检查结果状态
            if result.get('status') == 'error':
                return jsonify(result), 500
            
            # 添加作文ID和状态
            result['essay_id'] = essay.id
            result['status'] = 'completed'
            
            return jsonify({
                "status": "success",
                "data": result
            }), 200
        
    except Exception as e:
        logger.error(f"作文批改API异常: {str(e)}")
        
        # 回滚数据库事务
        db.session.rollback()
        
        return jsonify({
            "status": "error",
            "message": "服务器内部错误",
            "error": str(e)
        }), 500

@correction_bp.route('/status/<int:essay_id>', methods=['GET'])
def get_essay_status(essay_id):
    """获取作文批改状态
    
    参数:
    - essay_id: 作文ID
    
    返回:
    {
        "status": "success",
        "data": {
            "essay_id": 1,
            "title": "作文标题",
            "status": "pending/processing/completed/failed",
            "task_id": "xxxx-xxxx-xxxx", // 任务ID，如果有
            "error": "错误信息", // 如果状态为failed
            "result": { ... } // 如果状态为completed，包含完整结果
        }
    }
    """
    try:
        # 查询作文
        essay = Essay.query.get(essay_id)
        
        if not essay:
            return jsonify({
                "status": "error",
                "message": "作文不存在"
            }), 404
        
        # 检查权限（仅允许作者或管理员访问）
        user_id = g.user.id if hasattr(g, 'user') and g.user.is_authenticated() else None
        is_admin = hasattr(g, 'user') and g.user.role == 'admin'
        
        if not is_admin and essay.user_id != user_id:
            return jsonify({
                "status": "error",
                "message": "无权访问此作文"
            }), 403
        
        # 准备状态数据
        status_data = {
            "essay_id": essay.id,
            "title": essay.title,
            "status": essay.status,
            "submission_time": essay.submission_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 根据状态添加不同的数据
        if essay.status == 'failed':
            status_data["error"] = essay.error_message
            
        elif essay.status == 'completed':
            # 如果完成，添加完整结果
            status_data["result"] = essay.to_dict()
            
        # 如果有任务ID，也返回
        if essay.task_id:
            status_data["task_id"] = essay.task_id
        
        return jsonify({
            "status": "success",
            "data": status_data
        }), 200
        
    except Exception as e:
        logger.error(f"获取作文状态失败，ID: {essay_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "服务器内部错误",
            "error": str(e)
        }), 500

@correction_bp.route('/history', methods=['GET'])
def get_user_essay_history():
    """获取用户的作文批改历史
    
    参数:
    - page: 页码，默认1
    - per_page: 每页数量，默认10
    
    返回:
    {
        "status": "success",
        "data": {
            "essays": [
                {
                    "essay_id": 1,
                    "title": "作文标题",
                    "submission_time": "2023-01-01 12:00:00",
                    "total_score": 85,
                    "grade": "良好",
                    "word_count": 250,
                    "status": "pending/processing/completed/failed"
                }
            ],
            "pagination": {
                "page": 1,
                "per_page": 10,
                "total_essays": 20,
                "total_pages": 2
            }
        }
    }
    """
    # 验证用户是否登录
    if not hasattr(g, 'user') or not g.user.is_authenticated():
        return jsonify({
            "status": "error",
            "message": "用户未登录"
        }), 401
    
    # 获取分页参数
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # 验证分页参数
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 50:
        per_page = 10
    
    try:
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 获取用户作文历史
        essays = correction_service.get_user_essays(
            user_id=g.user.id,
            limit=per_page,
            offset=offset
        )
        
        # 获取总数
        with db.session.no_autoflush:
            total_essays = Essay.query.filter_by(user_id=g.user.id).count()
        
        # 计算总页数
        total_pages = (total_essays + per_page - 1) // per_page
        
        return jsonify({
            "status": "success",
            "data": {
                "essays": essays,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_essays": total_essays,
                    "total_pages": total_pages
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取用户作文历史失败: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "服务器内部错误",
            "error": str(e)
        }), 500

@correction_bp.route('/detail/<int:essay_id>', methods=['GET'])
def get_essay_detail(essay_id):
    """获取作文详情
    
    参数:
    - essay_id: 作文ID
    
    返回:
    {
        "status": "success",
        "data": {
            // 作文完整信息
        }
    }
    """
    # 验证用户是否登录
    if not hasattr(g, 'user') or not g.user.is_authenticated():
        return jsonify({
            "status": "error",
            "message": "用户未登录"
        }), 401
    
    try:
        # 获取作文详情
        essay_detail = correction_service.get_essay_by_id(essay_id)
        
        if not essay_detail:
            return jsonify({
                "status": "error",
                "message": "作文不存在"
            }), 404
        
        # 验证是否是自己的作文或管理员
        if essay_detail['user_id'] != g.user.id and g.user.role != 'admin':
            return jsonify({
                "status": "error",
                "message": "无权访问此作文"
            }), 403
        
        return jsonify({
            "status": "success",
            "data": essay_detail
        }), 200
        
    except Exception as e:
        logger.error(f"获取作文详情失败，ID: {essay_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "服务器内部错误",
            "error": str(e)
        }), 500
