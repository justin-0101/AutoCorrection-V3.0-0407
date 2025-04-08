#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改系统主应用入口
整合了所有模块，提供Web界面和API端点
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, g, session, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename
import secrets
import dotenv

# 导入项目模块
from config.app_config import APP_CONFIG, AI_CONFIG, USER_CONFIG
from config.logging_config import configure_logging, get_error_logger
from core.correction_controller import correction_controller
from core.user_model import User
from core.essay_model import Essay
from core.auth import login_required, admin_required, authenticate_user, register_user
from api import register_all_routes

# 加载环境变量
dotenv.load_dotenv()

# 创建Flask应用
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# 配置应用
app.secret_key = APP_CONFIG.get('SECRET_KEY', secrets.token_hex(16))
app.permanent_session_lifetime = timedelta(days=APP_CONFIG.get('SESSION_LIFETIME_DAYS', 30))
app.config['UPLOAD_FOLDER'] = APP_CONFIG.get('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = APP_CONFIG.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)  # 默认16MB

# 配置CORS
CORS(app)

# 配置日志
configure_logging()
logger = logging.getLogger('autocorrection.app')
error_logger = get_error_logger()

# 注册所有API路由
register_all_routes(app)

# 创建必要的目录
def create_required_directories():
    """创建应用所需的所有目录"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        'logs',
        'instance',
        'static',
        'templates'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"确保目录存在: {directory}")

# 在每个请求前检查用户会话和数据库连接
@app.before_request
def before_request():
    """每个请求前的预处理"""
    # 如果用户已登录，检查会话中的用户信息
    if 'user_id' in session:
        user_id = session.get('user_id')
        g.user = User.find_by_id(user_id)
        if not g.user:
            # 如果用户不存在，清除会话
            session.clear()
    else:
        g.user = None

# 主页路由
@app.route('/')
def index():
    """渲染首页"""
    user = g.get('user')
    
    # 获取用户最近的作文（如果已登录）
    recent_essays = []
    if user:
        essays = Essay.find_by_user_id(user.id, limit=5)
        recent_essays = [essay.to_dict(include_content=False) for essay in essays]
    
    return render_template('index.html', 
                          user=user, 
                          recent_essays=recent_essays)

# 用户登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    # 如果用户已登录，重定向到首页
    if g.get('user'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # 验证用户
            user_data = authenticate_user(email, password)
            
            # 设置会话
            session.permanent = True
            session['user_id'] = user_data['user_id']
            session['username'] = user_data['username']
            session['user_type'] = user_data['user_type']
            
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'登录失败: {str(e)}', 'danger')
    
    return render_template('login.html')

# 用户注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    # 如果用户已登录，重定向到首页
    if g.get('user'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # 验证表单数据
        if not username or not email or not password:
            flash('请填写所有必填字段', 'danger')
        elif password != password_confirm:
            flash('两次输入的密码不匹配', 'danger')
        else:
            try:
                # 注册用户
                user_data = register_user(username, email, password)
                
                # 设置会话
                session.permanent = True
                session['user_id'] = user_data['user_id']
                session['username'] = user_data['username']
                session['user_type'] = user_data['user_type']
                
                flash('注册成功！', 'success')
                return redirect(url_for('index'))
                
            except Exception as e:
                flash(f'注册失败: {str(e)}', 'danger')
    
    return render_template('register.html')

# 用户登出路由
@app.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    flash('您已成功登出', 'info')
    return redirect(url_for('index'))

# 作文批改页面
@app.route('/correction', methods=['GET', 'POST'])
@login_required
def correction():
    """作文批改页面"""
    user = g.user
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        grade = request.form.get('grade', 'junior')
        
        if not content:
            flash('请输入作文内容', 'danger')
            return render_template('correction.html', user=user)
        
        # 提交作文批改
        success, message, essay_id = correction_controller.submit_correction(
            user_id=user.id,
            title=title,
            content=content,
            grade=grade
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('correction_result', essay_id=essay_id))
        else:
            flash(message, 'danger')
    
    return render_template('correction.html', user=user)

# 作文批改结果页面
@app.route('/correction/result/<int:essay_id>')
@login_required
def correction_result(essay_id):
    """作文批改结果页面"""
    user = g.user
    
    # 获取作文结果
    result = correction_controller.get_correction_result(essay_id, user.id)
    
    if result.get('success'):
        return render_template('correction_result.html', 
                              user=user, 
                              result=result)
    else:
        flash(result.get('message', '无法获取批改结果'), 'danger')
        return redirect(url_for('correction'))

# 用户历史记录页面
@app.route('/history')
@login_required
def user_history():
    """用户作文历史记录页面"""
    user = g.user
    page = request.args.get('page', 1, type=int)
    limit = 10
    offset = (page - 1) * limit
    
    # 获取用户作文列表
    result = correction_controller.list_user_corrections(user.id, limit, offset)
    
    # 计算总页数
    total_pages = (result.get('total', 0) + limit - 1) // limit
    
    return render_template('history.html', 
                          user=user, 
                          essays=result.get('essays', []),
                          total=result.get('total', 0),
                          page=page,
                          total_pages=total_pages)

# 文件上传批改路由
@app.route('/correction/upload', methods=['POST'])
@login_required
def correction_upload():
    """处理文件上传批改"""
    user = g.user
    
    if 'file' not in request.files:
        flash('未找到上传文件', 'danger')
        return redirect(url_for('correction'))
    
    file = request.files['file']
    if file.filename == '':
        flash('未选择文件', 'danger')
        return redirect(url_for('correction'))
    
    # 检查文件类型
    allowed_extensions = ['txt', 'docx']
    file_ext = os.path.splitext(file.filename)[1].lower()[1:]
    if file_ext not in allowed_extensions:
        flash(f'不支持的文件类型，请上传 {", ".join(allowed_extensions)} 格式的文件', 'danger')
        return redirect(url_for('correction'))
    
    # 获取其他表单参数
    title = request.form.get('title', os.path.splitext(file.filename)[0])
    grade = request.form.get('grade', 'junior')
    
    try:
        # 创建上传目录
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # 保存文件
        filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
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
            os.remove(file_path)
            flash('文件内容为空或过短，请确保文件包含足够的文本内容', 'danger')
            return redirect(url_for('correction'))
        
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
                
            flash(message, 'success')
            return redirect(url_for('correction_result', essay_id=essay_id))
        else:
            # 删除文件
            os.remove(file_path)
            flash(message, 'danger')
            return redirect(url_for('correction'))
            
    except Exception as e:
        logger.error(f"文件上传处理错误: {str(e)}", exc_info=True)
        flash(f'文件处理错误: {str(e)}', 'danger')
        return redirect(url_for('correction'))

# 运行应用
if __name__ == '__main__':
    # 创建必要的目录
    create_required_directories()
    
    # 日志记录启动信息
    logger.info('-' * 50)
    logger.info('作文批改系统启动')
    logger.info(f'版本: 2.0')
    logger.info(f'环境: {os.environ.get("FLASK_ENV", "development")}')
    logger.info('-' * 50)
    
    # 启动Flask应用
    app.run(debug=True, host='0.0.0.0', port=5000) 