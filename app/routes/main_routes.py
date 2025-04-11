#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主路由模块
包含网站的主要页面路由，例如首页、关于页面等
"""

from flask import Blueprint, render_template, current_app, session, redirect, url_for, flash, request, jsonify
from urllib.parse import urlparse
import logging
import traceback
import json
from flask_login import login_required, current_user, login_user, logout_user
import os
from app.extensions import db
from werkzeug.utils import secure_filename
from datetime import datetime
from app.core.auth.auth_service import AuthService
from app.core.auth.exceptions import AuthenticationError, AuthorizationError, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash
from app.core.correction.file_service import FileService
from app.core.correction.correction_service import CorrectionService
from app.utils.input_sanitizer import sanitize_input

# 导入文档处理模块
from app.utils.document_processor import process_document, extract_text_from_txt, extract_text_from_docx, extract_text_from_doc

# 创建蓝图
main_bp = Blueprint('main', __name__)

# 配置日志记录器
logger = logging.getLogger('app')

# Import necessary models
from app.models.essay import Essay, EssaySourceType, EssayStatus
from app.models.correction import Correction, CorrectionType, CorrectionStatus
from app.models.user import User, UserProfile

@main_bp.route('/')
def index():
    """首页路由"""
    try:
        # 这里可以传递一些变量给模板，例如 recent_essays, stats, logged_in
        # logged_in = 'user_id' in session
        # user = ... # 获取用户信息
        # recent_essays = ... # 获取最近作文
        # stats = ... # 获取统计数据
        return render_template('index.html') #, logged_in=logged_in, user=user, recent_essays=recent_essays, stats=stats)
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Failed to render index.html. Error: {e}\nTraceback:\n{tb}")
        return "Welcome to the Essay Correction System! (Error rendering template)"

@main_bp.route('/about')
def about():
    """关于页面路由"""
    try:
        return render_template('about.html')
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Failed to render about.html. Error: {e}\nTraceback:\n{tb}")
        return "About the Essay Correction System. (Error rendering template)"

# --- 添加缺失的路由 --- 

@main_bp.route('/correction', methods=['GET', 'POST'])
@login_required
def correction():
    """作文批改页面"""
    logger.info("Correction route accessed with method: %s", request.method)
    
    # 检查用户是否已登录
    if not current_user or not current_user.is_authenticated:
        logger.warning("用户未登录或认证失败")
        flash('请先登录', 'error')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        logger.info("Processing correction form submission")
        
        try:
            # 记录表单数据
            logger.info("接收到表单数据: %s", request.form)
            logger.info("表单键值: %s", list(request.form.keys()))
            
            # 获取并验证source_type
            source_type = request.form.get('source_type', 'text')
            logger.info("表单中的原始source_type值: '%s'", source_type)
            
            # 清理source_type值
            source_type = sanitize_input(source_type, max_length=20)
            logger.info("清理后的source_type: 从 '%s' 到 '%s'", request.form.get('source_type'), source_type)
            
            # 验证source_type值
            valid_types = ['text', 'upload', 'paste', 'api']
            logger.info("有效的source_type值: %s", valid_types)
            
            if source_type not in valid_types:
                source_type = 'text'  # 默认为text类型
            
            logger.info("source_type值有效: '%s'", source_type)
            
            if 'file' in request.files:
                file = request.files['file']
                if file:
                    logger.info("处理文件上传: %s", file.filename)
                    
                    # 处理文件
                    file_service = FileService()
                    file_result = file_service.process_uploaded_file(file)
                    
                    if file_result.get('success'):
                        title = file_result.get('title', '')
                        logger.info("文件处理成功: %s, 标题: %s", file.filename, title)
                        
                        # 使用source_type
                        logger.info("文件上传 - 使用source_type值: '%s'", source_type)
                        
                        # 使用作文标题
                        title = title or request.form.get('subject', '')
                        logger.info("使用作文标题: %s", title)
                        
                        try:
                            # 创建作文记录
                            correction_service = CorrectionService()
                            result = correction_service.submit_essay(
                                user_id=current_user.id,
                                title=title,
                                content=file_result['content'],
                                grade='junior'  # 默认为初中水平
                            )
                            
                            if result.get('status') == 'success':
                                logger.info("异步批改任务已提交，essay_id: %s, task_id: %s", 
                                          result.get('essay_id'), result.get('task_id'))
                                
                                # 设置成功消息
                                flash('作文已提交并开始批改，请稍候...', 'success')
                                logger.info("File processed successfully: %s", file.filename)
                                
                                # 返回JSON响应而不是重定向
                                return jsonify({
                                    'success': True,
                                    'message': '作文已提交并开始批改，请稍候...',
                                    'essay_id': result['essay_id'],
                                    'task_id': result.get('task_id')
                                })
                            else:
                                # 返回错误JSON响应
                                return jsonify({
                                    'success': False,
                                    'message': result.get('message', '提交失败')
                                })
                        except Exception as e:
                            logger.error("创建作文记录时出错: %s", str(e), exc_info=True)
                            # 返回错误JSON响应
                            return jsonify({
                                'success': False,
                                'message': '提交作文时出错，请重试'
                            })
                            
            # 返回错误JSON响应
            return jsonify({
                'success': False,
                'message': '请选择要上传的文件'
            })
            
        except Exception as e:
            logger.error("处理作文提交时出错: %s", str(e), exc_info=True)
            # 返回错误JSON响应
            return jsonify({
                'success': False,
                'message': '处理文件时出错，请重试'
            })
    
    # GET请求处理
    remaining_info = None
    if current_user.is_authenticated:
        try:
            remaining_info = {
                'user_type': current_user.membership_level,
                'total_remaining': current_user.get_remaining_corrections(),
                'daily_remaining': current_user.get_daily_remaining_corrections()
            }
        except Exception as e:
            logger.error("获取用户剩余批改次数时出错: %s", str(e), exc_info=True)
            remaining_info = {
                'user_type': 'unknown',
                'total_remaining': 0,
                'daily_remaining': 0
            }
    
    return render_template('correction.html', remaining_info=remaining_info)

@main_bp.route('/batch_upload', methods=['GET', 'POST'])
def batch_upload():
    """批量上传作文处理"""
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return jsonify({
                'success': False,
                'error': '请至少选择一个文件上传'
            })
            
        files = request.files.getlist('files[]')
        if not files or all(not f.filename for f in files):
            return jsonify({
                'success': False,
                'error': '请至少选择一个文件上传'
            })
            
        # 检查文件数量限制
        if len(files) > 10:
            return jsonify({
                'success': False,
                'error': '一次最多只能上传10个文件'
            })
            
        results = []
        success_count = 0
        error_count = 0
        
        for file in files:
            if not file or not file.filename:
                continue
                
            try:
                # 验证文件
                if not allowed_file(file.filename):
                    raise ValueError(f'不支持的文件格式：{file.filename}')
                
                # 保存文件并处理内容
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                try:
                    # 处理文件内容
                    content, file_title = process_document(file_path)
                    if not content:
                        raise ValueError('文件处理失败，内容为空')
                    
                    # 创建Essay记录
                    essay = Essay(
                        title=file_title or os.path.splitext(filename)[0],
                        content=content,
                        user_id=current_user.id,
                        source_type=EssaySourceType.upload,
                        status=EssayStatus.PENDING.value
                    )
                    db.session.add(essay)
                    db.session.flush()  # 获取essay.id
                    
                    # 创建Correction记录
                    correction = Correction(
                        essay_id=essay.id,
                        type=CorrectionType.AI.value,
                        status=CorrectionStatus.PENDING.value
                    )
                    db.session.add(correction)
                    db.session.flush()  # 获取correction.id
                    
                    # 提交批改任务
                    from app.tasks.correction_tasks import process_essay_correction
                    task = process_essay_correction.delay(essay.id)
                    
                    # 更新任务ID
                    correction.task_id = task.id
                    db.session.commit()
                    
                    # 记录成功结果
                    results.append({
                        'filename': filename,
                        'status': 'processing',
                        'essay_id': essay.id,
                        'task_id': task.id
                    })
                    success_count += 1
                    current_app.logger.info(f"成功处理文件: {filename}, essay_id: {essay.id}, task_id: {task.id}")
                    
                except Exception as e:
                    db.session.rollback()
                    raise ValueError(f'处理失败: {str(e)}')
                    
                finally:
                    # 清理临时文件
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        current_app.logger.error(f"清理临时文件失败: {str(e)}")
            
            except Exception as e:
                error_message = str(e)
                current_app.logger.error(f"处理文件失败 {file.filename}: {error_message}")
                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'error': error_message
                })
                error_count += 1
        
        # 返回处理结果
        response_data = {
            'success': True,
            'results': results,
            'total': len(files),
            'success_count': success_count,
            'error_count': error_count
        }
        
        # 设置闪现消息
        if success_count > 0:
            if error_count == 0:
                flash(f'成功上传并开始处理 {success_count} 个文件', 'success')
            else:
                flash(f'成功上传 {success_count} 个文件，{error_count} 个文件失败', 'warning')
        else:
            flash('所有文件上传失败', 'danger')
        
        return jsonify(response_data)
    
    # GET请求：显示上传页面
    return render_template(
        'batch_upload.html',
        max_files=10,
        max_file_size=5 * 1024 * 1024,  # 5MB
        allowed_extensions=['txt', 'doc', 'docx']
    )

def allowed_file(filename):
    """检查文件是否允许上传"""
    ALLOWED_EXTENSIONS = {'txt', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/history')
@login_required
def user_history():
    """用户作文历史记录页面"""
    try:
        # 获取当前用户的作文，按创建时间倒序排列
        essays = Essay.query.filter_by(user_id=current_user.id).order_by(Essay.created_at.desc()).all()
        
        # 添加预览内容（限制文本长度）
        for essay in essays:
            # 截取作文内容前200个字符作为预览
            if len(essay.content) > 200:
                essay.preview = essay.content[:200] + '...'
            else:
                essay.preview = essay.content
        
        # 传递作文列表到模板
        try:
            return render_template('user_history.html', essays=essays)
        except Exception as template_error:
            current_app.logger.error(f"模板渲染失败: {template_error}")
            # 尝试使用带路径的模板名
            return render_template('/user_history.html', essays=essays)
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Failed to render user_history.html. Error: {e}\nTraceback:\n{tb}")
        return render_template('error.html', error_code=500, error_message="加载历史记录时出错，请稍后再试。")

@main_bp.route('/membership')
@login_required
def membership():
    """会员中心页面"""
    try:
        # 获取用户信息
        user = User.query.get(current_user.id)
        if not user:
            flash('用户信息获取失败', 'danger')
            return redirect(url_for('main.index'))
        
        # 如果用户没有会员信息，创建默认会员信息
        if not user.membership:
            from app.models.membership import Membership
            from datetime import datetime, timedelta
            
            # 查询免费计划
            from app.models.membership import MembershipPlan
            free_plan = MembershipPlan.query.filter_by(name='Free').first()
            if not free_plan:
                # 如果没有免费计划，创建一个
                free_plan = MembershipPlan(
                    name='Free',
                    code='FREE',
                    price=0,
                    duration_days=365,
                    max_essays_per_day=3,
                    max_essays_total=10,
                    description='免费会员计划'
                )
                db.session.add(free_plan)
                db.session.commit()
            
            # 创建默认免费会员
            default_membership = Membership(
                user_id=user.id,
                plan_id=free_plan.id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=365)  # 设置一年有效期
            )
            db.session.add(default_membership)
            db.session.commit()
            user = User.query.get(current_user.id)  # 重新获取用户信息
        
        # 准备用户信息 - 保持相同的结构，只是更改字段引用
        user_info = {
            'username': user.username,
            'user_type': user.membership.plan.name if user.membership and user.membership.plan else 'Free',
            'essays_remaining': user.membership.plan.max_essays_total - user.membership.essays_used_total if user.membership and user.membership.plan else 5,
            'essays_total': user.membership.plan.max_essays_total if user.membership and user.membership.plan else 5,
            'essays_total_used': user.membership.essays_used_total if user.membership else 0,
            'expiration_date': user.membership.end_date.strftime('%Y-%m-%d') if user.membership and user.membership.end_date else '永久有效',
            'essays_daily_used': user.membership.essays_used_today if user.membership else 0,
            'essays_daily_limit': user.membership.plan.max_essays_per_day if user.membership and user.membership.plan else 3,
            'vip_status': 0 if not user.membership or user.membership.plan.name == 'Free' else 1
        }
        
        # 配置信息
        config = {
            'free_essays': 10,
            'free_daily_limit': 3,
            'regular_monthly_essays': 100,
            'regular_daily_essays': 10,
            'premium_monthly_essays': 'unlimited',
            'premium_daily_essays': 'unlimited'
        }
        
        return render_template('membership.html', user=user_info, config=config)
    except Exception as e:
        current_app.logger.error(f"Failed to render membership.html. Error: {str(e)}\nTraceback:\n{traceback.format_exc()}")
        flash('获取会员信息失败', 'danger')
        return render_template('error.html', error_code=500, error_message="获取会员信息时出错。")

@main_bp.route('/profile')
def profile():
    """个人资料页面"""
    try:
        # 获取当前用户信息
        if current_user.is_authenticated:
            user = User.query.get(current_user.id)
            # 确保获取用户的profile，如果不存在则创建一个
            if not hasattr(user, 'profile') or not user.profile:
                profile = UserProfile(user_id=user.id)
                db.session.add(profile)
                db.session.commit()
                # 重新查询用户以获取更新后的关系
                user = User.query.get(current_user.id)
            
            return render_template('profile.html', user=user, profile=user.profile)
        else:
            flash('请先登录', 'warning')
            return redirect(url_for('main.login'))
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Failed to render profile.html. Error: {e}\nTraceback:\n{tb}")
        return "Error rendering profile page."

@main_bp.route('/results/<int:essay_id>')
@login_required
def results(essay_id):
    """批改结果页面"""
    try:
        # Fetch the essay and its correction results
        essay = Essay.query.get_or_404(essay_id)
        
        # Optional: Check if the current user owns this essay
        if essay.user_id != current_user.id:
            flash('您没有权限查看此作文的结果。', 'danger')
            return redirect(url_for('main.user_history'))
        
        correction = Correction.query.filter_by(essay_id=essay_id).first()
        
        if not correction or not correction.results:
            flash('找不到该作文的批改结果或结果仍在处理中。', 'warning')
            # Redirect to history or another appropriate page
            return redirect(url_for('main.user_history'))
            
        # Assuming correction.results is stored as a JSON string
        try:
            results_data = json.loads(correction.results)
        except json.JSONDecodeError:
            current_app.logger.error(f"Failed to decode JSON results for essay {essay_id}")
            flash('无法解析批改结果数据。', 'danger')
            return redirect(url_for('main.user_history'))

        # Pass all necessary data to the template
        return render_template(
            'results.html', 
            essay=essay,
            correction=correction,
            results=results_data,
            # 确保从results_data中提取所有需要的字段
            total_score=results_data.get('total_score', 0),
            grade=results_data.get('level', 'N/A'),
            content_score=results_data.get('content_score', 0),
            language_score=results_data.get('language_score', 0),
            structure_score=results_data.get('structure_score', 0),
            writing_score=results_data.get('writing_score', 0),
            overall_assessment=results_data.get('overall_assessment', ''),
            content_analysis=results_data.get('content_analysis', ''),
            language_analysis=results_data.get('language_analysis', ''),
            structure_analysis=results_data.get('structure_analysis', ''),
            writing_analysis=results_data.get('writing_analysis', ''),
            content=essay.content,
            word_count=len(essay.content),
            spelling_errors=results_data.get('spelling_errors', {'解析': []})
        )
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Failed to render results.html for essay {essay_id}. Error: {e}\nTraceback:\n{tb}")
        return render_template('error.html', error_code=500, error_message=f"加载作文 {essay_id} 结果时出错。请稍后再试或联系管理员。")

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    # 检查用户是否已经登录
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            login_type = request.form.get('login_type', 'password')
            # 记录登录尝试，不包含密码
            current_app.logger.info(f"用户尝试登录: {request.form.get('username')}, 登录类型: {login_type}")
            
            # 使用AuthService进行用户认证
            auth_service = AuthService()
            user = auth_service.authenticate(
                request.form.get('username'),
                request.form.get('password')
            )
            
            if user:
                # 更新用户登录信息
                user.last_login_at = datetime.now()
                user.last_login_ip = request.remote_addr
                db.session.commit()
                
                # 设置session变量（不依赖roles属性）
                session['user_id'] = user.id
                session['username'] = user.username
                
                # 设置角色信息
                if user.is_admin:
                    session['role'] = 'admin'
                else:
                    session['role'] = 'user'
                
                # 使用Flask-Login登录用户
                login_user(user, remember=bool(request.form.get('remember')))
                
                # 尝试生成令牌但不中断登录流程
                try:
                    token = auth_service.generate_token(user)
                    session['token'] = token
                except Exception as token_err:
                    current_app.logger.error(f"无法生成用户令牌: {str(token_err)}")
                
                flash('登录成功！', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.index'))
            else:
                flash('登录失败，请检查您的用户名和密码。', 'danger')
        except Exception as e:
            current_app.logger.error(f"登录过程中出现错误: {str(e)}", exc_info=True)
            flash('服务器错误，请稍后再试。', 'danger')
    
    return render_template('login.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # 验证密码匹配
            if password != confirm_password:
                flash('两次输入的密码不匹配', 'danger')
                return render_template('register.html')
            
            # 验证用户名和邮箱是否已存在
            if User.query.filter_by(username=username).first():
                flash('用户名已存在', 'danger')
                return render_template('register.html')
            
            if User.query.filter_by(email=email).first():
                flash('邮箱已被注册', 'danger')
                return render_template('register.html')
            
            # 创建新用户
            user = User(
                username=username,
                email=email,
                is_active=True,
                created_at=datetime.now()
            )
            
            # 设置密码
            user.set_password(password)
            
            # 保存用户到数据库以获取user.id
            db.session.add(user)
            db.session.flush()
            
            # 创建用户资料
            profile = UserProfile(user_id=user.id)
            user.profile = profile
            
            # 保存所有更改
            db.session.add(profile)
            db.session.commit()
            
            flash('注册成功，请登录', 'success')
            return redirect(url_for('main.login'))
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"注册过程中出现错误: {str(e)}", exc_info=True)
            flash('服务器错误，请稍后再试', 'danger')
    
    return render_template('register.html')

@main_bp.route('/logout')
@login_required
def logout():
    """登出"""
    # 清除 session 变量
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    
    # 使用 Flask-Login 的 logout_user 函数
    logout_user()
    
    flash('您已成功退出登录。', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """忘记密码页面"""
    if request.method == 'POST':
        # 处理忘记密码表单提交
        flash('密码重置功能尚未完全实现', 'warning')
        return redirect(url_for('main.login'))
    try:
        return render_template('forgot_password.html')
    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Failed to render forgot_password.html. Error: {e}\nTraceback:\n{tb}")
        return "Error rendering forgot password page."

@main_bp.route('/retry_correction/<int:essay_id>')
@login_required
def retry_correction(essay_id):
    """重新批改作文"""
    try:
        # 获取作文
        essay = Essay.query.get_or_404(essay_id)
        
        # 检查权限
        if essay.user_id != current_user.id:
            flash('您没有权限重新批改此作文', 'danger')
            return redirect(url_for('main.user_history'))
        
        # 更新作文状态
        essay.status = 'pending'
        
        # 获取或创建批改记录
        correction = Correction.query.filter_by(essay_id=essay.id).first()
        if not correction:
            correction = Correction(essay_id=essay.id, type='ai')
            db.session.add(correction)
        
        # 提交更改
        db.session.commit()
        
        try:
            # 导入并启动异步批改任务
            from app.tasks.correction_tasks import process_essay_correction
            result = process_essay_correction.apply_async(args=[essay.id])
            current_app.logger.info(f"重新批改任务已提交，essay_id: {essay.id}, task_id: {result.id}")
        except Exception as task_error:
            current_app.logger.error(f"异步任务提交失败: {str(task_error)}")
            # 如果异步任务失败，尝试同步执行
            try:
                from app.core.correction.correction_service import CorrectionService
                corrector = CorrectionService()
                corrector.perform_correction(essay.id)
                current_app.logger.info(f"同步执行重新批改，essay_id: {essay.id}")
            except Exception as e:
                current_app.logger.error(f"同步批改失败: {str(e)}")
                flash('批改过程出现错误，请稍后再试', 'danger')
                return redirect(url_for('main.user_history'))
        
        flash('作文已重新提交批改，请稍后查看结果', 'success')
        return redirect(url_for('main.user_history'))
        
    except Exception as e:
        current_app.logger.error(f"重新批改作文时出错: {str(e)}")
        flash('重新批改作文时出错，请稍后再试', 'danger')
        return redirect(url_for('main.user_history'))

@main_bp.route('/delete_essay/<int:essay_id>', methods=['POST'])
@login_required
def delete_essay(essay_id):
    essay = Essay.query.get_or_404(essay_id)
    
    # 验证当前用户是否有权限删除这篇作文
    if essay.user_id != current_user.id:
        flash('您没有权限删除这篇作文', 'danger')
        return redirect(url_for('main.user_history'))
    
    try:
        # 删除相关的批改记录
        Correction.query.filter_by(essay_id=essay_id).delete()
        # 删除作文
        db.session.delete(essay)
        db.session.commit()
        flash('作文已成功删除', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除作文时发生错误: {str(e)}')
        flash('删除作文时发生错误', 'danger')
    
    return redirect(url_for('main.user_history'))

@main_bp.route('/batch_delete_essays', methods=['POST'])
@login_required
def batch_delete_essays():
    essay_ids = request.form.get('essay_ids', '')
    if not essay_ids:
        flash('未选择要删除的作文', 'warning')
        return redirect(url_for('main.user_history'))
    
    try:
        essay_id_list = [int(id) for id in essay_ids.split(',')]
        deleted_count = 0
        
        for essay_id in essay_id_list:
            essay = Essay.query.get(essay_id)
            if essay and essay.user_id == current_user.id:
                # 删除相关的批改记录
                Correction.query.filter_by(essay_id=essay_id).delete()
                # 删除作文
                db.session.delete(essay)
                deleted_count += 1
        
        db.session.commit()
        flash(f'成功删除 {deleted_count} 篇作文', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'批量删除作文时发生错误: {str(e)}')
        flash('删除作文时发生错误', 'danger')
    
    return redirect(url_for('main.user_history'))

@main_bp.route('/api/v1/correction/essays/status/<int:essay_id>')
@login_required
def get_essay_status(essay_id):
    """获取作文批改状态API"""
    try:
        essay = Essay.query.get_or_404(essay_id)
        
        # 检查用户权限
        if essay.user_id != current_user.id and not current_user.is_admin:
            return jsonify({
                'success': False,
                'message': '没有权限查看此作文'
            })
        
        # 获取批改状态
        status = essay.status
        correction = Correction.query.filter_by(essay_id=essay_id).first()
        
        return jsonify({
            'success': True,
            'status': status,
            'correction_id': correction.id if correction else None
        })
    except Exception as e:
        logger.error(f"获取作文状态时出错: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'获取作文状态时出错: {str(e)}'
        }), 500

# 可以在这里添加更多主路由... 