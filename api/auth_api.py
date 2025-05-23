"""
认证API模块
提供用户注册、登录、登出和密码重置功能
"""

from flask import Blueprint, request, jsonify, current_app, g, session
import logging
from datetime import datetime, timedelta
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

from app.models.user import User, UserProfile
from app.models.login import LoginHistory
from app.extensions import db
from utils.validators import validate_email, validate_password, validate_username
from utils.exceptions import AuthenticationError, ValidationError, api_error_handler

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 获取logger
logger = logging.getLogger(__name__)

@auth_bp.route('/register', methods=['POST'])
@api_error_handler
def register():
    """用户注册
    
    请求体:
    {
        "username": "用户名",
        "email": "邮箱",
        "password": "密码",
        "fullName": "姓名",
        "school": "学校",
        "grade": "年级"
    }
    
    返回:
    {
        "status": "success",
        "message": "注册成功",
        "data": {
            "user_id": 1,
            "username": "用户名",
            "email": "邮箱",
            "token": "JWT令牌"
        }
    }
    """
    data = request.get_json()
    
    if not data:
        raise ValidationError("未提供注册数据")
    
    # 获取注册信息
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('fullName')
    school = data.get('school')
    grade = data.get('grade')
    
    # 验证输入
    username_validation = validate_username(username)
    if not username_validation['valid']:
        raise ValidationError(username_validation['message'])
    
    email_validation = validate_email(email)
    if not email_validation['valid']:
        raise ValidationError(email_validation['message'])
    
    password_validation = validate_password(password)
    if not password_validation['valid']:
        raise ValidationError(password_validation['message'])
    
    # 检查用户名和邮箱是否已存在
    with db.session.no_autoflush:
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                raise ValidationError("用户名已被使用")
            else:
                raise ValidationError("邮箱已被注册")
    
    try:
        # 创建新用户
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.flush()  # 获取用户ID
        
        # 创建用户资料
        profile = UserProfile(
            user_id=user.id,
            full_name=full_name,
            school=school,
            grade=grade
        )
        db.session.add(profile)
        
        # 提交事务
        db.session.commit()
        
        # 生成JWT令牌
        token = generate_auth_token(user)
        
        # 记录登录
        record_login(user.id)
        
        logger.info(f"新用户注册成功: {username} (ID: {user.id})")
        
        return jsonify({
            "status": "success",
            "message": "注册成功",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "token": token
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"用户注册失败: {str(e)}")
        raise ValidationError(f"注册失败: {str(e)}")

@auth_bp.route('/login', methods=['POST'])
@api_error_handler
def login():
    """用户登录
    
    请求体:
    {
        "email": "邮箱",
        "password": "密码"
    }
    
    返回:
    {
        "status": "success",
        "message": "登录成功",
        "data": {
            "user_id": 1,
            "username": "用户名",
            "email": "邮箱",
            "role": "用户角色",
            "token": "JWT令牌"
        }
    }
    """
    data = request.get_json()
    
    if not data:
        raise ValidationError("未提供登录数据")
    
    # 获取登录信息
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        raise ValidationError("邮箱和密码不能为空")
    
    # 查找用户
    with db.session.no_autoflush:
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            raise AuthenticationError("邮箱或密码不正确")
        
        if not user.is_active:
            raise AuthenticationError("账号已被禁用")
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # 生成JWT令牌
    token = generate_auth_token(user)
    
    # 记录登录
    record_login(user.id)
    
    logger.info(f"用户登录成功: {user.username} (ID: {user.id})")
    
    return jsonify({
        "status": "success",
        "message": "登录成功",
        "data": {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "token": token
        }
    })

@auth_bp.route('/profile', methods=['GET'])
@api_error_handler
def get_profile():
    """获取用户资料
    
    请求头:
    Authorization: Bearer <token>
    
    返回:
    {
        "status": "success",
        "data": {
            "user": {
                "id": 1,
                "username": "用户名",
                "email": "邮箱",
                "role": "用户角色",
                "created_at": "2023-01-01 12:00:00",
                "last_login": "2023-01-01 12:00:00",
                "is_active": true
            },
            "profile": {
                "full_name": "姓名",
                "school": "学校",
                "grade": "年级",
                "subscription_expires": "2023-01-01 12:00:00",
                "essay_count": 10,
                "essay_monthly_limit": 5,
                "essay_monthly_used": 3,
                "reset_date": "2023-01-01"
            }
        }
    }
    """
    # 验证用户是否登录
    if not hasattr(g, 'user') or not g.user:
        raise AuthenticationError("未登录或会话已过期")
    
    user = g.user
    
    # 获取用户资料
    with db.session.no_autoflush:
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        
        if not profile:
            # 创建默认资料
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()
    
    # 转换为字典
    user_dict = user.to_dict()
    profile_dict = profile.to_dict() if profile else {}
    
    # 移除敏感信息
    if 'id' in profile_dict:
        del profile_dict['id']
    if 'user_id' in profile_dict:
        del profile_dict['user_id']
    
    return jsonify({
        "status": "success",
        "data": {
            "user": user_dict,
            "profile": profile_dict
        }
    })

@auth_bp.route('/profile', methods=['PUT'])
@api_error_handler
def update_profile():
    """更新用户资料
    
    请求头:
    Authorization: Bearer <token>
    
    请求体:
    {
        "fullName": "姓名",
        "school": "学校",
        "grade": "年级"
    }
    
    返回:
    {
        "status": "success",
        "message": "资料更新成功"
    }
    """
    # 验证用户是否登录
    if not hasattr(g, 'user') or not g.user:
        raise AuthenticationError("未登录或会话已过期")
    
    data = request.get_json()
    
    if not data:
        raise ValidationError("未提供更新数据")
    
    user = g.user
    
    # 获取要更新的字段
    full_name = data.get('fullName')
    school = data.get('school')
    grade = data.get('grade')
    
    # 更新用户资料
    with db.session.no_autoflush:
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        
        if not profile:
            # 创建默认资料
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
        
        # 更新字段（只更新提供的字段）
        if full_name is not None:
            profile.full_name = full_name
        if school is not None:
            profile.school = school
        if grade is not None:
            profile.grade = grade
        
        # 提交更新
        db.session.commit()
    
    logger.info(f"用户资料更新成功: {user.username} (ID: {user.id})")
    
    return jsonify({
        "status": "success",
        "message": "资料更新成功"
    })

@auth_bp.route('/change-password', methods=['PUT'])
@api_error_handler
def change_password():
    """修改密码
    
    请求头:
    Authorization: Bearer <token>
    
    请求体:
    {
        "currentPassword": "当前密码",
        "newPassword": "新密码"
    }
    
    返回:
    {
        "status": "success",
        "message": "密码修改成功"
    }
    """
    # 验证用户是否登录
    if not hasattr(g, 'user') or not g.user:
        raise AuthenticationError("未登录或会话已过期")
    
    data = request.get_json()
    
    if not data:
        raise ValidationError("未提供密码数据")
    
    user = g.user
    
    # 获取密码信息
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    
    if not current_password or not new_password:
        raise ValidationError("当前密码和新密码不能为空")
    
    # 验证当前密码
    if not user.check_password(current_password):
        raise ValidationError("当前密码不正确")
    
    # 验证新密码
    password_validation = validate_password(new_password)
    if not password_validation['valid']:
        raise ValidationError(password_validation['message'])
    
    # 更新密码
    user.set_password(new_password)
    db.session.commit()
    
    logger.info(f"用户密码修改成功: {user.username} (ID: {user.id})")
    
    return jsonify({
        "status": "success",
        "message": "密码修改成功"
    })

# JWT相关函数
def generate_auth_token(user, expiration=86400):
    """生成JWT令牌
    
    Args:
        user: 用户对象
        expiration: 过期时间（秒）
        
    Returns:
        str: JWT令牌
    """
    from config.app_config import APP_CONFIG
    
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(seconds=expiration)
    }
    
    return jwt.encode(
        payload,
        APP_CONFIG['SECRET_KEY'],
        algorithm='HS256'
    )

def decode_auth_token(token):
    """解码JWT令牌
    
    Args:
        token: JWT令牌
        
    Returns:
        dict: 解码后的数据
    """
    from config.app_config import APP_CONFIG
    
    try:
        payload = jwt.decode(
            token,
            APP_CONFIG['SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("令牌已过期")
    except jwt.InvalidTokenError:
        raise AuthenticationError("无效的令牌")

def record_login(user_id):
    """记录登录记录
    
    Args:
        user_id: 用户ID
    """
    try:
        # 获取IP地址和用户代理
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # 创建登录记录
        login_record = LoginHistory(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(login_record)
        db.session.commit()
    except Exception as e:
        logger.error(f"记录登录失败: {str(e)}")
        db.session.rollback()  # 回滚事务，但不影响主流程

# 认证中间件
@auth_bp.before_app_request
def load_logged_in_user():
    """从请求中加载已登录用户"""
    # 检查Authorization头
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ')[1]
        
        try:
            # 解析令牌
            payload = decode_auth_token(token)
            user_id = payload.get('user_id')
            
            # 获取用户信息
            with db.session.no_autoflush:
                user = User.query.filter_by(id=user_id).first()
                
                if user and user.is_active:
                    g.user = user
                    return
        except Exception as e:
            logger.error(f"认证令牌解析失败: {str(e)}")
    
    # 如果没有有效的令牌，清除g.user
    g.user = None
