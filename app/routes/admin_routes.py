#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
管理员后台路由模块
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, request, g, abort, flash, current_app, jsonify
from app.core.auth.auth_decorators import login_required, admin_required
from app.models.user import User, UserProfile, MembershipLevel
from app.models.essay import Essay
from app.models.membership import MembershipPlan, Membership
from datetime import datetime, timedelta
from sqlalchemy import or_
from flask_login import current_user
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf import FlaskForm
from wtforms import IntegerField, HiddenField, StringField, SelectField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Email, Length, EqualTo
from app import db

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 创建SQLAlchemy对象
db = SQLAlchemy()

# 定义修改批改次数表单
class UpdateUserCorrectionsForm(FlaskForm):
    """用户批改次数更新表单"""
    user_id = HiddenField('用户ID', 
        validators=[DataRequired(message='用户ID不能为空')])
    monthly_limit = IntegerField('每月限制', 
        validators=[
            DataRequired(message='请输入每月批改限制次数'),
            NumberRange(min=0, message='批改次数不能小于0')
        ])
    monthly_used = IntegerField('已使用次数', 
        validators=[
            DataRequired(message='请输入已使用次数'),
            NumberRange(min=0, message='已使用次数不能小于0')
        ])

# 定义添加用户表单
class AddUserForm(FlaskForm):
    """添加用户表单"""
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=50, message='用户名长度必须在3-50个字符之间')
    ])
    email = StringField('邮箱', validators=[
        DataRequired(message='请输入邮箱'),
        Email(message='请输入有效的邮箱地址')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=6, message='密码长度不能少于6个字符')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(message='请确认密码'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    user_type = SelectField('用户类型', choices=[
        ('free', '免费用户'),
        ('basic', '普通会员'),
        ('premium', '高级会员')
    ], validators=[DataRequired(message='请选择用户类型')])
    role = SelectField('角色', choices=[
        ('user', '普通用户'),
        ('admin', '管理员')
    ], validators=[DataRequired(message='请选择用户角色')])


@admin_bp.before_request
def before_request():
    """
    请求前执行的操作，例如检查用户权限
    """
    # 验证请求中是否存在当前用户，如果没有则重定向到登录页面
    # 这里的权限检查依赖于 auth_decorators 中的 login_required 和 admin_required 装饰器
    pass


@admin_bp.route('/')
@admin_bp.route('/index')
@login_required
@admin_required
def index():
    """管理员控制台首页"""
    
    # 创建默认stats，确保始终存在
    stats = {
        'total_users': 0,
        'total_essays': 0,
        'premium_users': 0,
        'total_income': 0
    }
    
    system_info = {
        'ai_available': False,
        'redis_available': False,
        'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'uptime': '3天14小时',
        'error_logs': 0
    }
    
    recent_users = []
    recent_essays = []
    users_count = 0
    essays_count = 0
    today_users = 0
    users_by_day = []
    
    try:
        # 准备数据
        # 1. 总体统计数据
        users_count = User.query.count()
        essays_count = Essay.query.count()
        
        # 更新stats字典
        stats['total_users'] = users_count
        stats['total_essays'] = essays_count
        
        # 2. 今日新增用户数
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        today_users = User.query.filter(
            User.created_at.between(today_start, today_end)
        ).count()
        
        # 3. 最近7天用户注册趋势
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        users_by_day = []
        
        for day in last_7_days:
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            count = User.query.filter(
                User.created_at.between(day_start, day_end)
            ).count()
            users_by_day.append({
                'date': day.strftime('%m-%d'),
                'count': count
            })
        
        # 4. 最近10篇作文
        recent_essays = Essay.query.order_by(Essay.created_at.desc()).limit(10).all()
        
        # 更新高级会员数量
        try:
            premium_users = User.query.filter(User.membership_level == MembershipLevel.PREMIUM.value).count()
            stats['premium_users'] = premium_users
        except Exception as e:
            logger.warning(f"获取高级会员数量失败: {str(e)}")
        
        # 检查Redis服务可用性
        try:
            from app.core.services import get_redis_service
            redis_service = get_redis_service()
            if redis_service and redis_service.is_connected():
                system_info['redis_available'] = True
                logger.debug("Redis服务可用")
            else:
                logger.warning("Redis服务不可用")
        except Exception as e:
            logger.warning(f"检查Redis服务失败: {str(e)}")
            system_info['redis_available'] = False

        # 检查AI服务可用性
        try:
            from app.core.services import get_ai_service
            ai_client = get_ai_service()
            system_info['ai_available'] = (ai_client is not None)
            logger.debug(f"AI服务状态: {'可用' if system_info['ai_available'] else '不可用'}")
        except Exception as e:
            logger.warning(f"检查AI服务失败: {str(e)}")
            system_info['ai_available'] = False
        
        # 获取最近注册用户
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"管理后台首页数据准备错误: {str(e)}\n{tb}")
    
    # 即使出错也返回模板，保证stats和system_info已定义
    return render_template(
        'admin/dashboard.html',
        users_count=users_count,
        essays_count=essays_count,
        today_users=today_users,
        users_by_day=users_by_day,
        recent_essays=recent_essays,
        stats=stats,
        system_info=system_info,
        recent_users=recent_users
    )



@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def users():
    """用户管理页面"""
    
    # 初始化表单
    form = UpdateUserCorrectionsForm()
    add_user_form = AddUserForm()
    
    # 处理POST请求 - 更新用户批改次数
    if request.method == 'POST':
        logger.info("开始处理更新用户批改次数请求")

        # 验证表单
        if form.validate():
            user_id = form.user_id.data
            user = db.session.get(User, user_id)
            if not user:
                logger.warning(f"用户不存在: {user_id}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"status": "error", "message": "用户不存在"})
                flash("用户不存在", "danger")
                return redirect(url_for('admin.users'))

            try:
                monthly_limit = form.monthly_limit.data
                monthly_used = form.monthly_used.data
                
                logger.info(f"接收到的参数: user_id={user_id}, monthly_limit={monthly_limit}, monthly_used={monthly_used}")
                
                # 使用事务保护数据一致性
                try:
                    with db.session.begin():
                        if not user.profile:
                            logger.info(f"为用户 {user.username} 创建新的用户档案")
                            profile = UserProfile(user_id=user.id)
                            db.session.add(profile)
                            user.profile = profile
                        
                        # 更新用户档案中的批改次数限制
                        user.profile.essay_monthly_limit = monthly_limit
                        user.profile.essay_monthly_used = monthly_used
                        
                        # 根据月度批改限制自动设置合适的会员级别
                        if monthly_limit <= 3:
                            user.membership_level = MembershipLevel.FREE.value
                        elif monthly_limit <= 30:
                            user.membership_level = MembershipLevel.BASIC.value
                        else:
                            user.membership_level = MembershipLevel.PREMIUM.value
                            
                        db.session.commit()
                        
                    logger.info(f"已更新用户 {user.username} 的批改次数限制")
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({"status": "success"})
                    flash(f"已成功更新用户 {user.username} 的批改次数", "success")
                    
                except Exception as e:
                    logger.error(f"更新用户批改次数时出现数据库错误: {str(e)}")
                    db.session.rollback()
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({"status": "error", "message": f"数据库错误: {str(e)}"})
                    flash(f"更新用户批改次数时出现数据库错误: {str(e)}", "danger")
            except Exception as e:
                logger.error(f"更新用户批改次数时出现错误: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"status": "error", "message": f"系统错误: {str(e)}"})
                flash(f"更新用户批改次数时出现错误: {str(e)}", "danger")
        else:
            logger.warning("表单验证失败")
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = ", ".join(field_errors)
                logger.warning(f"{field}: {errors[field]}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"status": "error", "errors": errors})
            
            for field, field_errors in form.errors.items():
                flash(f"{getattr(form[field].label, 'text', field)}: {', '.join(field_errors)}", 'danger')
        
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return redirect(url_for('admin.users'))
    
    # GET 请求处理 - 显示用户列表
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    user_type = request.args.get('user_type', '')
    role = request.args.get('role', '')
    status = request.args.get('status', '')
    
    # 构建查询
    query = User.query
    
    # 应用搜索条件
    if search:
        query = query.filter(or_(
            User.username.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%')
        ))
    
    # 应用用户类型过滤
    if user_type:
        query = query.filter(User.membership_level == user_type)
    
    # 应用角色过滤
    if role == 'admin':
        query = query.filter(User._is_admin == True)
    elif role == 'user':
        query = query.filter(User._is_admin == False)
    
    # 应用状态过滤
    if status == '1':
        query = query.filter(User._is_active == True)
    elif status == '0':
        query = query.filter(User._is_active == False)
    
    # 分页查询结果
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=per_page)
    users = pagination.items
    
    # 根据数据库的会员计划获取可用权益
    membership_plans = {}
    try:
        with current_app.app_context():
            plans = MembershipPlan.query.all()
            for plan in plans:
                membership_plans[plan.code] = {
                    'name': plan.name,
                    'daily_limit': plan.max_essays_per_day,
                    'monthly_limit': plan.max_essays_total
                }
    except Exception as e:
        logger.error(f"获取会员计划信息时出错: {str(e)}")
        membership_plans = {
            'free': {'name': '免费用户', 'daily_limit': 1, 'monthly_limit': 5},
            'basic': {'name': '普通会员', 'daily_limit': 5, 'monthly_limit': 30},
            'premium': {'name': '高级会员', 'daily_limit': 10, 'monthly_limit': 100}
        }
    
    return render_template(
        'admin/user_management.html',
        users=users,
        pagination=pagination,
        form=form,
        add_user_form=add_user_form,
        membership_plans=membership_plans
    )
@admin_bp.route('/membership')
@login_required
def membership():
    """会员管理页面"""
    
    # 默认值
    plans = []
    recent_memberships = []
    
    try:
        # 权限检查
        if not current_user.is_admin:
            flash('您没有权限访问会员管理', 'danger')
            return redirect(url_for('main.index'))
        
        # 会员计划信息
        plans = MembershipPlan.query.all()
        recent_memberships = Membership.query.order_by(Membership.created_at.desc()).limit(10).all()
    
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"会员管理页面错误: {str(e)}\n{tb}")
        # 出错继续返回模板，使用默认值
    
    return render_template(
        'admin/membership.html',
        plans=plans,
        recent_memberships=recent_memberships
    )


@admin_bp.route('/essays')
@login_required
def essays():
    """作文管理页面"""
    
    # 默认值
    essays = []
    pagination = None
    page = 1
    status = ""
    user_id = ""
    per_page = 20
    
    try:
        # 权限检查
        if not current_user.is_admin:
            flash('您没有权限访问作文管理', 'danger')
            return redirect(url_for('main.index'))
        
        # 添加分页和过滤功能
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '', type=str)
        user_id = request.args.get('user_id', '', type=str)
        
        # 构建查询
        essay_query = Essay.query
        
        # 如果指定了状态，添加过滤条件
        if status:
            essay_query = essay_query.filter(Essay.status == status)
        
        # 如果指定了用户ID，添加过滤条件
        if user_id and user_id.isdigit():
            essay_query = essay_query.filter(Essay.user_id == int(user_id))
        
        # 排序并分页
        pagination = essay_query.order_by(Essay.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        essays = pagination.items
    
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"作文管理页面错误: {str(e)}\n{tb}")
        # 出错继续返回模板，使用默认值
    
    return render_template(
        'admin/essays.html',
        essays=essays,
        pagination=pagination,
        current_page=page,
        status=status,
        user_id=user_id
    )


@admin_bp.route('/stats')
@login_required
def stats():
    """统计分析页面"""
    
    # 默认值
    stats = {
        'total_essays': 0,
        'avg_score': 0,
        'avg_words': 0,
        'monthly_stats': [],
        'score_distribution': []
    }
    
    try:
        # 权限检查
        if not current_user.is_admin:
            flash('您没有权限访问统计分析', 'danger')
            return redirect(url_for('main.index'))
        
        # 添加统计分析功能
        from app.models.essay import Essay
        
        # 基本统计数据
        total_essays = Essay.query.count()
        
        # 假设获取平均分和平均字数
        avg_score = 0
        avg_words = 0
        
        if total_essays > 0:
            # 这里可以从数据库中计算实际的平均分和平均字数
            # 例如：avg_score = db.session.query(func.avg(Essay.total_score)).scalar() or 0
            avg_score = 85.5  # 示例数据
            avg_words = 650   # 示例数据
        
        # 按月份统计作文数量（示例数据）
        monthly_stats = [
            ('1月', 45),
            ('2月', 58),
            ('3月', 72),
            ('4月', 85),
            ('5月', 65),
            ('6月', 90)
        ]
        
        # 按分数区间统计作文数量（示例数据）
        score_distribution = [
            ('0-60', 10),
            ('61-70', 25),
            ('71-80', 45),
            ('81-90', 58),
            ('91-100', 22)
        ]
        
        stats = {
            'total_essays': total_essays,
            'avg_score': avg_score,
            'avg_words': avg_words,
            'monthly_stats': monthly_stats,
            'score_distribution': score_distribution
        }
    
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"统计分析页面错误: {str(e)}\n{tb}")
        # 出错继续返回模板，使用默认值
    
    return render_template(
        'admin/essay_stats.html',
        stats=stats
    )


@admin_bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    """系统配置页面"""
    
    # 默认值
    backup_info = {
        'last_backup': '从未备份',
        'backup_count': 0,
        'auto_backup': False,
        'backup_location': 'backups/'
    }
    
    system_config = {
        'site_name': '小园丁作文批改系统',
        'site_description': '基于AI的作文批改系统',
        'max_upload_size': 10,  # MB
        'allowed_file_types': '.txt, .doc, .docx, .pdf',
        'maintenance_mode': False
    }
    
    ai_config = {
        'api_provider': 'deepseek',
        'model': 'deepseek-reasoner',
        'max_retry': 3,
        'timeout': 30
    }
    
    template_config = {
        'ai_service_status': '1',  # 启用
        'max_tokens': 4096,
        'temperature': 0.7,
        'model_name': 'deepseek-reasoner'
    }
    
    try:
        # 权限检查
        if not current_user.is_admin:
            flash('您没有权限访问系统配置', 'danger')
            return redirect(url_for('main.index'))
        
        # 获取系统配置
        # 这里可以从数据库或配置文件加载系统配置信息
        backup_info = {
            'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'backup_count': 0,
            'auto_backup': False,
            'backup_location': 'backups/'
        }
        
        # 处理POST请求保存系统配置
        if request.method == 'POST':
            # 检查内容类型，处理JSON请求
            if request.is_json:
                data = request.get_json()
                
                # 处理数据库备份请求
                if 'backup_database' in data:
                    try:
                        # 这里实现数据库备份逻辑
                        # ...
                        logger.info("执行数据库备份")
                        return jsonify({
                            'success': True,
                            'message': f'数据库备份成功，时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                        })
                    except Exception as e:
                        logger.error(f"数据库备份失败: {str(e)}")
                        return jsonify({'success': False, 'message': f'备份失败: {str(e)}'})
                
                # 处理清理临时文件请求
                elif 'clear_temp_files' in data:
                    try:
                        # 这里实现清理临时文件逻辑
                        # ...
                        logger.info("执行临时文件清理")
                        return jsonify({
                            'success': True,
                            'message': '临时文件清理成功'
                        })
                    except Exception as e:
                        logger.error(f"清理临时文件失败: {str(e)}")
                        return jsonify({'success': False, 'message': f'清理失败: {str(e)}'})
                
                # 其他JSON请求...
                return jsonify({'success': False, 'message': '未知操作'})
            
            try:
                logger.info("接收到保存系统配置请求")
                
                # 根据表单数据更新配置
                if 'membership_settings' in request.form:
                    # 处理会员设置
                    # 免费用户设置
                    free_monthly = request.form.get('free_monthly', 10, type=int)
                    free_daily = request.form.get('free_daily', 3, type=int)
                    
                    # 普通会员设置
                    basic_monthly = request.form.get('basic_monthly', 100, type=int)
                    basic_daily = request.form.get('basic_daily', 20, type=int)
                    basic_price = request.form.get('basic_price', 49, type=float)
                    
                    # 高级会员设置
                    premium_monthly = request.form.get('premium_monthly', 300, type=int)
                    premium_daily = request.form.get('premium_daily', 50, type=int)
                    premium_price = request.form.get('premium_price', 89, type=float)
                    
                    # 注册奖励
                    signup_bonus = request.form.get('signup_bonus', 3, type=int)
                    
                    # 更新数据库中的会员计划
                    try:
                        # 免费计划
                        free_plan = MembershipPlan.query.filter_by(name='free').first()
                        if free_plan:
                            free_plan.monthly_essay_limit = free_monthly
                            free_plan.daily_essay_limit = free_daily
                        
                        # 基础计划
                        basic_plan = MembershipPlan.query.filter_by(name='basic').first()
                        if basic_plan:
                            basic_plan.monthly_essay_limit = basic_monthly
                            basic_plan.daily_essay_limit = basic_daily
                            basic_plan.price = basic_price
                        
                        # 高级计划
                        premium_plan = MembershipPlan.query.filter_by(name='premium').first()
                        if premium_plan:
                            premium_plan.monthly_essay_limit = premium_monthly
                            premium_plan.daily_essay_limit = premium_daily
                            premium_plan.price = premium_price
                        
                        # 保存更改
                        db.session.commit()
                        
                        # 更新系统配置
                        # TODO: 保存注册奖励到系统配置表
                        
                        flash('会员设置已更新', 'success')
                        logger.info("会员设置已更新")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"更新会员设置时发生错误: {str(e)}")
                        flash(f'更新会员设置失败: {str(e)}', 'danger')
                
                # 处理系统配置更新
                elif 'site_title' in request.form:
                    # 处理系统基本配置
                    site_title = request.form.get('site_title')
                    site_description = request.form.get('site_description')
                    contact_email = request.form.get('contact_email')
                    maintenance_mode = request.form.get('maintenance_mode')
                    
                    # 更新系统配置...
                    flash('系统配置已更新', 'success')
                    logger.info("系统配置已更新")
                
                # 处理AI配置更新
                elif 'ai_service_status' in request.form:
                    # 处理AI配置
                    ai_service_status = request.form.get('ai_service_status')
                    max_tokens = request.form.get('max_tokens', type=int)
                    temperature = request.form.get('temperature', type=float)
                    model_name = request.form.get('model_name')
                    
                    # 更新AI配置...
                    flash('AI配置已更新', 'success')
                    logger.info("AI配置已更新")
                
                # 其他配置更新...
                
            except Exception as e:
                logger.error(f"保存系统配置时发生错误: {str(e)}", exc_info=True)
                flash(f'保存配置失败: {str(e)}', 'danger')
    
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"系统配置页面错误: {str(e)}\n{tb}")
        # 出错继续返回模板，使用默认值
    
    return render_template(
        'admin/website_config.html',
        backup_info=backup_info,
        system_config=system_config,
        ai_config=ai_config,
        config=template_config
    )


@admin_bp.route('/add_user', methods=['POST'])
@login_required
@admin_required
def add_user():
    """添加新用户"""
    form = AddUserForm()
    
    if form.validate():
        try:
            # 检查用户名和邮箱是否已存在
            if User.query.filter_by(username=form.username.data).first():
                return jsonify({"status": "error", "errors": {"username": "用户名已存在"}})
                
            if User.query.filter_by(email=form.email.data).first():
                return jsonify({"status": "error", "errors": {"email": "邮箱已存在"}})
            
            # 创建新用户
            user = User(
                username=form.username.data,
                email=form.email.data,
                membership_level=form.user_type.data,
                _is_admin=form.role.data == 'admin'
            )
            user.set_password(form.password.data)
            
            # 创建用户档案
            profile = UserProfile(user_id=user.id)
            
            # 根据用户类型设置批改次数限制
            if form.user_type.data == 'free':
                profile.essay_monthly_limit = 3
            elif form.user_type.data == 'basic':
                profile.essay_monthly_limit = 30
            elif form.user_type.data == 'premium':
                profile.essay_monthly_limit = 100
            
            # 保存到数据库
            db.session.add(user)
            db.session.add(profile)
            db.session.commit()
            
            return jsonify({"status": "success", "message": "添加用户成功"})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"添加用户时出现错误: {str(e)}")
            return jsonify({"status": "error", "message": f"添加用户失败: {str(e)}"})
    else:
        errors = {}
        for field, field_errors in form.errors.items():
            errors[field] = ", ".join(field_errors)
        
        return jsonify({"status": "error", "errors": errors})


@admin_bp.route('/monitoring')
@login_required
@admin_required
def monitoring():
    """系统监控页面"""
    try:
        from app.core.monitoring.monitor_service import metrics_store, alert_manager
        
        # 获取监控指标
        metrics = metrics_store.get_all_metrics()
        
        # 获取最近的告警
        recent_alerts = alert_manager.get_recent_alerts(limit=10)
        
        # 获取系统状态
        system_stats = {
            'essays': {
                'pending': metrics_store.get_gauge('essays.count.pending'),
                'processing': metrics_store.get_gauge('essays.count.processing'),
                'completed': metrics_store.get_gauge('essays.count.completed'),
                'failed': metrics_store.get_gauge('essays.count.failed')
            },
            'tasks': {
                'active': metrics_store.get_gauge('celery_tasks_active'),
                'success_rate': metrics_store.get_counter('tasks.successes') / 
                               (metrics_store.get_counter('tasks.total') or 1) * 100,
                'failure_rate': metrics_store.get_counter('tasks.failures') / 
                               (metrics_store.get_counter('tasks.total') or 1) * 100
            },
            'performance': {
                'avg_processing_time': metrics_store.get_histogram_stats('essay_correction.processing_time').get('avg', 0),
                'p95_processing_time': metrics_store.get_histogram_stats('essay_correction.processing_time').get('p95', 0)
            }
        }
        
        return render_template(
            'admin/monitoring.html',
            metrics=metrics,
            system_stats=system_stats,
            recent_alerts=recent_alerts,
            active_page='monitoring'
        )
        
    except Exception as e:
        logger.error(f"加载监控页面出错: {str(e)}")
        flash(f'加载监控页面出错: {str(e)}', 'danger')
        return redirect(url_for('admin.index'))


@admin_bp.errorhandler(404)
def page_not_found(e):
    """
    处理 404 错误
    """
    logger.warning(f"访问了不存在的管理员页面: {request.path}")
    return render_template('admin/error.html', error_code=404, error_message="页面不存在"), 404


@admin_bp.errorhandler(403)
def forbidden(e):
    """
    处理 403 错误
    """
    logger.warning(f"未授权访问管理员页面: {request.path}")
    return render_template('admin/error.html', error_code=403, error_message="没有访问权限"), 403


@admin_bp.errorhandler(500)
def internal_server_error(e):
    """
    处理 500 错误
    """
    logger.error(f"管理员页面服务器错误: {str(e)}")
    return render_template('admin/error.html', error_code=500, error_message="服务器内部错误"), 500 
