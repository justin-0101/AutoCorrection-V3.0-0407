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
from flask_wtf.csrf import generate_csrf

# 导入文档处理模块
from app.utils.document_processor import process_document, extract_text_from_txt, extract_text_from_docx, extract_text_from_doc, allowed_file

# 创建蓝图
main_bp = Blueprint('main', __name__)

# 配置日志记录器
logger = logging.getLogger('app')

# Import necessary models
from app.models.essay import Essay, EssaySourceType, EssayStatus
from app.models.correction import Correction, CorrectionType, CorrectionStatus
from app.models.user import User, UserProfile

# Import form classes
from app.forms import EssayCorrectionForm

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
    """处理作文批改请求"""
    # 导入依赖
    import os
    from flask import current_app, request, session, flash, redirect, url_for, jsonify
    # 导入EssaySourceType和EssayStatus
    from app.models import Essay, User, EssaySourceType, EssayStatus
    # 修改导入路径，从 app.forms 导入 EssayCorrectionForm
    from app.forms import EssayCorrectionForm
    from flask_login import current_user
    # 修改文件处理工具的导入
    from app.utils.file_handler import FileHandler
    from app.tasks.correction_tasks import process_essay_correction
    
    # 初始化表单
    form = EssayCorrectionForm()
    
    # 初始化文件处理器
    file_handler = FileHandler()
    
    # 会员信息展示 - 使用current_user而不是security
    user_id = current_user.id
    user = User.query.get(user_id)
    
    # 正确获取会员信息和批改限制
    remaining_info = {
        'user_type': user.membership_level or 'free',  # 使用membership_level而不是membership_type
        'total_remaining': user.get_remaining_corrections(),  # 使用用户方法获取剩余次数
        'daily_remaining': user.get_daily_remaining_corrections()  # 使用用户方法获取每日剩余次数
    }
    
    # 处理POST请求
    if request.method == 'POST':
        try:
            logger.info(f"接收到提交请求: {request.form}")
            
            # 记录提交的数据，便于调试
            logger.debug(f"表单数据: {request.form}")
            logger.debug(f"文件数据: {request.files}")
            logger.debug(f"CSRF Token: {form.csrf_token.current_token}")
            
            # 表单验证处理
            if not form.validate_on_submit():
                logger.error(f"表单验证失败: {form.errors}")
                # 将表单错误记录到日志中，便于调试
                for field, errors in form.errors.items():
                    for error in errors:
                        logger.error(f"表单字段 {field} 错误: {error}")
                
                # 如果是CSRF错误，提供更明确的错误信息
                if 'csrf_token' in form.errors:
                    error_msg = "CSRF验证失败。请刷新页面后重试。"
                    logger.error(f"CSRF Error: {form.csrf_token.errors}")
                    logger.error(f"Expected token: {form.csrf_token.current_token}")
                    logger.error(f"Received token: {request.form.get('csrf_token', 'None')}")
                else:
                    error_msg = "表单验证失败，请检查输入。"
                
                flash(error_msg, 'danger')
                return render_template('correction.html', form=form, remaining_info=remaining_info), 400
            
            # 提取表单数据
            source_type = request.form.get('source_type', 'upload')
            subject = request.form.get('subject', '未命名作文')
            
            # 判断是否是文件上传
            if source_type == 'upload' and 'file' in request.files:
                file = request.files['file']
                
                # 检查文件是否存在
                if file.filename == '':
                    flash('未选择文件', 'warning')
                    return render_template('correction.html', form=form, remaining_info=remaining_info)
                
                # 检查文件类型
                # 使用自定义逻辑获取文件扩展名
                file_extension = os.path.splitext(file.filename)[1].lower()
                if file_extension not in ['.txt', '.doc', '.docx', '.pdf']:
                    flash('不支持的文件类型，仅支持 .txt, .doc, .docx, .pdf 格式', 'warning')
                    return render_template('correction.html', form=form, remaining_info=remaining_info)
                
                # --- 检查会员剩余批改次数限制（管理员跳过） ---
                if not user.is_admin:
                    remaining_corrections = user.get_remaining_corrections()
                    if remaining_corrections <= 0:
                        flash('您的批改次数已用完，请升级会员或等待次月刷新', 'warning')
                        return render_template('correction.html', form=form, remaining_info=remaining_info)
                    
                    daily_remaining = user.get_daily_remaining_corrections()
                    if daily_remaining <= 0:
                        flash('您今日的批改次数已用完，请明天再试或升级会员获取更多次数', 'warning')
                        return render_template('correction.html', form=form, remaining_info=remaining_info)
                else:
                    logger.info(f"管理员用户 {user_id} 跳过批改次数限制检查")
                # -------------------------------------------------
                
                # 处理文件并保存
                try:
                    # 生成临时文件名和存储路径
                    base_path = current_app.config['UPLOAD_FOLDER']
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    filename = f"{user_id}_{timestamp}{file_extension}"
                    filepath = os.path.join(base_path, filename)
                    
                    # 确保目录存在
                    os.makedirs(base_path, exist_ok=True)
                    
                    # 保存文件
                    file.save(filepath)
                    logger.info(f"文件已保存: {filepath}")

                    # --- 读取文件字节内容 --- 
                    file.stream.seek(0) # 确保从文件开头读取
                    file_bytes = file.read() # 读取文件的所有字节
                    # -----------------------

                    # 读取文件内容（现在传递字节）
                    try:
                        # 使用FileHandler处理文件内容
                        file_info = file_handler.process_file(file_bytes, file.filename, save_file=False)
                        if not file_info or 'content' not in file_info:
                            raise ValueError("无法从文件提取内容")
                        essay_content = file_info['content']
                        file_size = file_info['size']
                        
                        # 提取文件名作为标题（如果表单未提供有效标题）
                        file_title = os.path.splitext(file.filename)[0]  # 直接使用原始文件名，不使用secure_filename
                        # 使用表单标题或文件名作为标题
                        essay_title = subject if subject and subject.strip() and subject != '未命名作文' else file_title
                        
                        logger.info(f"使用标题: {essay_title}, 来源: {'表单输入' if essay_title == subject else '文件名'}")
                        
                        # 创建Essay记录 (使用 essay_content)
                        essay = Essay(
                            title=essay_title,
                            content=essay_content, # 使用读取到的内容
                            user_id=user_id,
                            status=EssayStatus.PENDING.value, # 使用枚举确保一致性
                            source_type=EssaySourceType.upload.value # 明确来源类型
                        )
                        
                        db.session.add(essay)
                        db.session.commit()
                        logger.info(f"Essay记录已创建: {essay.id}")
                        
                        # 更新用户的批改次数（如果有profile）
                        if user.profile:
                            # 如果不是无限制用户，则扣减次数
                            if not user.profile.is_subscription_active():
                                user.profile.essay_monthly_used += 1
                                db.session.commit()
                                logger.info(f"用户 {user_id} 批改次数已更新，剩余 {user.get_remaining_corrections()} 次")
                        
                        # 创建异步批改任务
                        logger.info(f"创建异步批改任务: {essay.id}")
                        process_essay_correction.delay(essay.id)
                        
                        flash('文件上传成功，批改进行中，请耐心等待通知', 'success')
                        return redirect(url_for('main.user_history'))
                        
                    except Exception as read_err:
                        logger.error(f"读取或处理文件内容失败: {read_err}")
                        flash(f"读取文件内容失败: {read_err}", 'danger')
                        return render_template('correction.html', form=form, remaining_info=remaining_info)
                except Exception as e:
                    logger.error(f"文件处理失败: {str(e)}")
                    flash(f'文件处理失败: {str(e)}', 'danger')
                    return render_template('correction.html', form=form, remaining_info=remaining_info)
            else:
                flash('未找到上传的文件', 'warning')
                return render_template('correction.html', form=form, remaining_info=remaining_info)
                
        except Exception as e:
            logger.error(f"作文批改请求处理异常: {str(e)}")
            flash(f'处理请求时发生错误: {str(e)}', 'danger')
            return render_template('correction.html', form=form, remaining_info=remaining_info)
    
    # GET请求，显示表单页面
    return render_template('correction.html', form=form, remaining_info=remaining_info)

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
                # 处理文件内容
                content, file_title = process_document(file)
                if not content:
                    raise ValueError('文件处理失败，内容为空')
                
                # 创建Essay记录
                essay = Essay(
                    title=file_title or os.path.splitext(secure_filename(file.filename))[0],
                    content=content,
                    user_id=current_user.id,
                    source_type=EssaySourceType.upload.value,
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
                task = process_essay_correction.apply_async(args=[essay.id])
                
                # 更新任务ID
                correction.task_id = task.id
                db.session.commit()
                
                # 记录成功结果
                results.append({
                    'filename': file.filename,
                    'status': 'processing',
                    'essay_id': essay.id,
                    'task_id': task.id
                })
                success_count += 1
                current_app.logger.info(f"成功处理文件: {file.filename}, essay_id: {essay.id}, task_id: {task.id}")
                
            except Exception as e:
                error_message = str(e)
                current_app.logger.error(f"处理文件失败 {file.filename}: {error_message}")
                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'error': error_message
                })
                error_count += 1
                if 'db' in locals():
                    db.session.rollback()
        
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
    csrf_token = generate_csrf() # 生成CSRF令牌
    
    # 获取会员剩余次数信息 (需要移到GET请求部分)
    remaining_info = None
    if current_user.is_authenticated:
        membership = current_user.membership
        if membership:
            remaining_info = membership.get_remaining_info()
        else:
            remaining_info = {
                'user_type': 'free',
                'total_remaining': 5,
                'daily_remaining': 1
            }
            
    return render_template(
        'batch_upload.html',
        max_files=10,
        max_file_size=5 * 1024 * 1024,  # 5MB
        allowed_extensions=['txt', 'doc', 'docx', 'pdf', 'jpg', 'jpeg', 'png'],
        csrf_token=csrf_token,  # 传递令牌到模板
        remaining_info=remaining_info # 传递会员信息
    )

@main_bp.route('/history')
@login_required
def user_history():
    """用户作文历史记录页面"""
    try:
        # 确保当前用户已登录且有ID
        if not current_user or not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('main.login'))
        
        # 获取当前用户的作文，按创建时间倒序排列，添加空值检查
        essays = Essay.query.filter_by(user_id=current_user.id).filter(Essay.created_at != None).order_by(Essay.created_at.desc()).all()
        
        # 添加预览内容（限制文本长度）
        valid_essays = []
        for essay in essays:
            if essay is None:
                continue
                
            # 确保作文有内容属性
            if not hasattr(essay, 'content') or essay.content is None:
                essay.content = ""
                essay.preview = "(无内容)"
            else:
                # 截取作文内容前200个字符作为预览
                if len(essay.content) > 200:
                    essay.preview = essay.content[:200] + '...'
                else:
                    essay.preview = essay.content
            
            valid_essays.append(essay)
        
        # 传递作文列表到模板
        try:
            return render_template('user_history.html', essays=valid_essays)
        except Exception as template_error:
            current_app.logger.error(f"模板渲染失败: {template_error}")
            # 检查模板是否存在
            for template_dir in current_app.jinja_loader.searchpath:
                template_path = os.path.join(template_dir, 'user_history.html')
                if os.path.exists(template_path):
                    current_app.logger.info(f"找到模板文件: {template_path}")
                else:
                    current_app.logger.warning(f"模板文件不存在: {template_path}")
                    
            # 尝试使用带路径的模板名或错误模板
            try:
                return render_template('/user_history.html', essays=valid_essays)
            except Exception:
                return render_template('error.html', 
                                       error_code=500, 
                                       error_message="渲染历史记录页面时出错，请联系管理员。")
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
    """显示作文批改结果"""
    try:
        essay = Essay.query.get_or_404(essay_id)
        
        # 检查权限
        if essay.user_id != current_user.id:
            flash('您没有权限查看该作文的批改结果。', 'warning')
            return redirect(url_for('main.user_history'))
        
        correction = Correction.query.filter_by(essay_id=essay_id).first()
        
        if not correction or not correction.results:
            flash('作文正在批改中，请稍后刷新页面查看结果。', 'info')
            return render_template('results.html', essay=essay, correction=None, results=None)
            
        # 解析批改结果
        try:
            results_data = json.loads(correction.results)
        except json.JSONDecodeError:
            current_app.logger.error(f"解析批改结果JSON数据失败，essay_id={essay_id}")
            flash('解析批改结果数据出错。', 'danger')
            return redirect(url_for('main.user_history'))

        # 渲染结果页面
        return render_template(
            'results.html', 
            essay=essay,
            correction=correction,
            results=results_data
        )
    except Exception as e:
        current_app.logger.error(f"显示批改结果时出错: {str(e)}")
        flash('加载批改结果时出错，请稍后重试。', 'danger')
        return redirect(url_for('main.user_history'))

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
                # 获取用户ID，避免在不同的数据库会话间使用相同的对象
                user_id = user.id
                
                # 仅在调试环境添加日志
                logger.debug(f"用户验证成功: {user_id}")
                
                # 使用Flask-Login登录用户，但不更新用户最后登录时间
                login_user(user, remember=bool(request.form.get('remember')))
                
                # 异步更新用户登录信息
                try:
                    # 使用单独的线程异步更新用户登录数据
                    from threading import Thread
                    update_thread = Thread(
                        target=update_login_info, 
                        args=(
                            user_id, 
                            datetime.now(), 
                            request.remote_addr,
                            current_app.config['SQLALCHEMY_DATABASE_URI']
                        )
                    )
                    update_thread.daemon = True  # 设置为守护线程
                    update_thread.start()
                    logger.info(f"已启动异步线程更新用户登录信息: {user_id}")
                except Exception as thread_err:
                    logger.error(f"启动异步更新线程失败: {str(thread_err)}")
                
                # 设置session变量
                session['user_id'] = user_id
                session['username'] = user.username
                
                # 设置角色信息
                if user.is_admin:
                    session['role'] = 'admin'
                else:
                    session['role'] = 'user'
                
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

def update_login_info(user_id, login_time, login_ip, db_uri):
    """
    异步更新用户登录信息
    
    Args:
        user_id: 用户ID
        login_time: 登录时间
        login_ip: 登录IP地址
        db_uri: 数据库连接URI
    """
    try:
        # 延迟导入以避免循环引用
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import NullPool
        
        # 创建不使用连接池的引擎
        engine = create_engine(db_uri, poolclass=NullPool)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # 延迟导入用户模型
            from app.models.user import User
            
            # 查询用户并更新登录信息
            user = session.query(User).get(user_id)
            if user:
                user.last_login_at = login_time
                user.last_login_ip = login_ip
                session.commit()
                logging.getLogger(__name__).info(f"异步更新用户登录信息成功: {user_id}")
            else:
                logging.getLogger(__name__).warning(f"异步更新登录信息失败: 用户 {user_id} 不存在")
        except Exception as db_error:
            session.rollback()
            logging.getLogger(__name__).error(f"异步更新用户登录信息时数据库错误: {str(db_error)}")
        finally:
            # 务必关闭会话和连接
            session.close()
            engine.dispose()
    except Exception as e:
        logging.getLogger(__name__).error(f"异步更新用户登录信息失败: {str(e)}")

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
def get_essay_status(essay_id):
    """获取作文批改状态API"""
    try:
        # 检查用户是否已登录
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'message': '用户未登录或会话已过期',
                'redirect': '/login'
            }), 401  # 401 Unauthorized
        
        # 使用filter_by而不是get_or_404，以更好地处理不存在的记录
        essay = Essay.query.filter_by(id=essay_id).first()
        
        if not essay:
            return jsonify({
                'success': False,
                'message': f'作文不存在，ID: {essay_id}'
            }), 404
        
        # 检查用户权限
        if essay.user_id != current_user.id and not current_user.is_admin:
            return jsonify({
                'success': False,
                'message': '没有权限查看此作文'
            }), 403
        
        # 获取批改状态
        status = essay.status
        correction = Correction.query.filter_by(essay_id=essay_id).first()
        
        logger.info(f"成功获取作文状态, essay_id: {essay_id}, 状态: {status}")
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

@main_bp.route('/debug/correction', methods=['GET', 'POST'])
def debug_correction():
    """调试作文批改提交"""
    import json
    from datetime import datetime
    
    if request.method == 'POST':
        # 记录所有请求信息
        debug_info = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'method': request.method,
            'path': request.path,
            'args': dict(request.args),
            'form': dict(request.form),
            'files': [f.filename for f in request.files.values()] if request.files else [],
            'cookies': dict(request.cookies),
            'headers': dict(request.headers)
        }
        
        # 记录到文件
        debug_dir = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads')).resolve() / 'debug'
        debug_dir.mkdir(exist_ok=True, parents=True)
        
        debug_file = debug_dir / f"debug_request_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, ensure_ascii=False, indent=2)
        
        # 处理上传的文件
        file = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = debug_dir / filename
                file.save(str(file_path))
                current_app.logger.info(f"已保存上传的文件: {file_path}")
        
        # 返回调试信息
        return jsonify({
            'status': 'debug_success',
            'message': '已记录调试信息',
            'debug_info': debug_info,
            'file_saved': bool(file and file.filename)
        })
    
    # GET请求 - 显示测试表单
    return render_template('correction.html', form=EssayCorrectionForm(), debug_mode=True)
