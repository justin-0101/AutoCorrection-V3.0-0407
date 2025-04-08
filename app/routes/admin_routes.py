#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
管理员后台路由模块
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, request, g, abort, flash, current_app, jsonify
from app.core.auth.auth_decorators import login_required, admin_required
from app.models.user import User, UserProfile
from app.models.essay import Essay
from datetime import datetime, timedelta
from sqlalchemy import or_
from flask_login import current_user
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf import FlaskForm
from wtforms import IntegerField, HiddenField
from wtforms.validators import DataRequired, NumberRange

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 创建SQLAlchemy对象
db = SQLAlchemy()


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
            from app.models.user import MembershipLevel
            premium_users = User.query.filter(User.membership_level == MembershipLevel.PREMIUM.value).count()
            stats['premium_users'] = premium_users
        except Exception as e:
            logger.warning(f"获取高级会员数量失败: {str(e)}")
        
        # 检查AI服务可用性 - 修复服务容器访问方法
        try:
            # 修改为直接通过导入服务而不是使用ServiceContainer
            from app.core.services import get_ai_service
            ai_client = get_ai_service()
            system_info['ai_available'] = (ai_client is not None)
        except Exception as e:
            # 忽略错误，保持默认值False
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
    
    # 处理POST请求 - 更新用户批改次数
    if request.method == 'POST':
        logger.info("开始处理更新用户批改次数请求")

        # 验证表单
        form = UpdateUserCorrectionsForm()
        if not form.validate():
            logger.warning("表单验证失败")
            for field, errors in form.errors.items():
                flash(f"{getattr(form[field].label, 'text', field)}: {', '.join(errors)}", 'danger')
            return redirect(url_for('admin.users'))

        user_id = form.user_id.data
        user = db.session.get(User, user_id)
        if not user:
            logger.warning(f"用户不存在: {user_id}")
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
                    
                    # 更新用户档案
                    user.profile.monthly_limit = monthly_limit
                    user.profile.monthly_used = monthly_used
                    user.profile.reset_date = datetime.now()
                    
                    # 立即提交更改
                    db.session.commit()
                    logger.info(f"成功更新用户 {user.username} 的批改次数: limit={monthly_limit}, used={monthly_used}")
                    flash(f'已成功更新用户 {user.username} 的批改次数', 'success')
                    
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"数据库错误: {str(e)}")
                flash('数据库错误，请稍后重试', 'danger')
                
        except Exception as e:
            logger.error(f"更新用户批改次数时发生错误: {str(e)}")
            flash('更新批改次数失败，请稍后重试', 'danger')
        
        logger.info("完成处理更新用户批改次数请求")
        return redirect(url_for('admin.users'))
    
    # 处理GET请求 - 显示用户列表
    # 默认值，确保始终存在
    users = []
    pagination = None
    page = 1
    query = ""
    per_page = 20
    
    try:
        # 添加分页和搜索功能
        page = request.args.get('page', 1, type=int)
        query = request.args.get('query', '', type=str)
        
        # 构建查询
        user_query = User.query
        
        # 如果有搜索词，添加过滤条件
        if query:
            user_query = user_query.filter(
                or_(
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%'),
                    User.name.ilike(f'%{query}%')
                )
            )
        
        # 排序并分页
        pagination = user_query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users = pagination.items
        
        # 创建表单实例
        form = UpdateUserCorrectionsForm()
    
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"用户管理页面错误: {str(e)}\n{tb}")
        # 异常处理后继续返回模板，使用默认值
    
    return render_template(
        'admin/user_management.html',
        users=users,
        pagination=pagination,
        current_page=page,
        query=query,
        form=form
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
        from app.models.membership import MembershipPlan, Membership
        
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


@admin_bp.route('/config')
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