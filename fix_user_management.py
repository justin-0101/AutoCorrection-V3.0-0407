#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
管理后台用户管理页面修复脚本
解决以下问题：
1. 用户类型和角色显示问题
2. 修改批改次数表单验证失败
3. 添加用户按钮无响应
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from flask_wtf import FlaskForm
from wtforms import IntegerField, HiddenField, StringField, SelectField, PasswordField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo

# 将当前目录添加到Python路径中
sys.path.append(os.getcwd())

# 导入应用
from app import create_app
from app.models.user import User, UserProfile, MembershipLevel
from app.models.membership import MembershipPlan
from app.models.db import db

# 创建应用实例
app = create_app()

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

def fix_user_management_template():
    """修复用户管理模板"""
    try:
        # 检查模板路径
        template_path = 'app/templates/admin/user_management.html'
        if not os.path.exists(template_path):
            print(f"未找到模板文件: {template_path}")
            return False
            
        # 读取模板内容
        with open(template_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 修复用户类型显示
        # 从 <td>{% if user.user_type == 'free' %}...{% endif %}</td>
        # 修改为显示用户会员级别和对应的批改次数限制
        type_display = '''<td>
            {% if user.membership_level == 'free' %}
            <span class="badge bg-secondary">免费用户</span>
            <small class="d-block text-muted">每日限制: 1篇</small>
            {% elif user.membership_level == 'basic' %}
            <span class="badge bg-primary">普通会员</span>
            <small class="d-block text-muted">每日限制: 5篇</small>
            {% elif user.membership_level == 'premium' %}
            <span class="badge bg-warning">高级会员</span>
            <small class="d-block text-muted">每日限制: 10篇</small>
            {% else %}
            <span class="badge bg-secondary">未知</span>
            {% endif %}
        </td>'''
        
        # 修复已使用次数表单显示
        # 确保表单字段正确显示和验证消息能够正常显示
        usage_display = '''<div class="mb-3">
            <label class="form-label">每月批改限制</label>
            <input type="number" class="form-control" id="monthly_limit" name="monthly_limit" 
                   value="{{ user.profile.essay_monthly_limit if user.profile else 3 }}" required min="0">
            <div class="invalid-feedback" id="monthly_limit_error"></div>
        </div>
        <div class="mb-3">
            <label class="form-label">当月已使用次数</label>
            <input type="number" class="form-control" id="monthly_used" name="monthly_used" 
                   value="{{ user.profile.essay_monthly_used if user.profile else 0 }}" required min="0">
            <div class="invalid-feedback" id="monthly_used_error"></div>
        </div>'''
        
        # 添加修改用户表单提交处理的JavaScript代码
        js_code = '''
<script>
document.addEventListener('DOMContentLoaded', function() {
    // 修复修改批改次数表单提交
    const correctionForms = document.querySelectorAll('.correction-form');
    correctionForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch('{{ url_for("admin.users") }}', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 显示成功消息
                    alert('修改成功');
                    // 关闭模态框
                    const modal = bootstrap.Modal.getInstance(this.closest('.modal'));
                    modal.hide();
                    // 刷新页面
                    window.location.reload();
                } else {
                    // 显示错误消息
                    if (data.errors) {
                        for (const field in data.errors) {
                            const errorElement = document.getElementById(field + '_error');
                            if (errorElement) {
                                errorElement.textContent = data.errors[field];
                                errorElement.parentElement.querySelector('input').classList.add('is-invalid');
                            }
                        }
                    } else {
                        alert(data.message || '修改失败');
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('提交请求出错，请重试');
            });
        });
    });
    
    // 修复添加用户按钮
    const addUserForm = document.getElementById('addUserForm');
    if (addUserForm) {
        addUserForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch('{{ url_for("admin.add_user") }}', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 显示成功消息
                    alert('添加用户成功');
                    // 关闭模态框
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
                    modal.hide();
                    // 刷新页面
                    window.location.reload();
                } else {
                    // 显示错误消息
                    if (data.errors) {
                        for (const field in data.errors) {
                            const errorElement = document.getElementById('add_' + field + '_error');
                            if (errorElement) {
                                errorElement.textContent = data.errors[field];
                                errorElement.parentElement.querySelector('input').classList.add('is-invalid');
                            }
                        }
                    } else {
                        alert(data.message || '添加用户失败');
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('提交请求出错，请重试');
            });
        });
    }
});
</script>
'''
        # 将修改添加到页面底部
        if '</html>' in content:
            content = content.replace('</html>', js_code + '</html>')
        else:
            content += js_code
            
        # 保存修改后的模板
        with open(template_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        print(f"模板文件修复成功: {template_path}")
        return True
    except Exception as e:
        print(f"修复模板时出错: {str(e)}")
        return False

def fix_admin_routes():
    """修复管理路由处理函数"""
    try:
        # 检查路由文件路径
        route_path = 'app/routes/admin_routes.py'
        if not os.path.exists(route_path):
            print(f"未找到路由文件: {route_path}")
            return False
            
        # 读取路由文件内容
        with open(route_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 修改users路由函数，添加对JSON请求的处理
        users_function = '''
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
        with app.app_context():
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
'''
        
        # 添加处理添加用户的路由
        add_user_route = '''
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
'''
        
        # 替换现有的users函数并添加add_user函数
        if '@admin_bp.route(\'/users\'' in content:
            # 找到users函数定义的起始位置
            start_idx = content.find('@admin_bp.route(\'/users\'')
            
            # 找到函数定义的结束位置（下一个函数定义的开始）
            next_route = content.find('@admin_bp.route(', start_idx + 1)
            if next_route == -1:
                end_idx = len(content)
            else:
                end_idx = next_route
                
            # 替换users函数定义
            content = content[:start_idx] + users_function + content[end_idx:]
            
            # 添加add_user函数
            content += add_user_route
        else:
            print("未找到users路由函数定义")
            return False
            
        # 保存修改后的路由文件
        with open(route_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        print(f"路由文件修复成功: {route_path}")
        return True
    except Exception as e:
        print(f"修复路由时出错: {str(e)}")
        return False

def main():
    """主函数"""
    print("开始修复管理后台用户管理页面...")
    
    template_fixed = fix_user_management_template()
    routes_fixed = fix_admin_routes()
    
    if template_fixed and routes_fixed:
        print("修复完成！请重启应用使更改生效。")
        return 0
    else:
        print("修复过程中出现错误，请查看日志。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 