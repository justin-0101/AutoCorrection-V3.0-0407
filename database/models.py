"""
数据库模型定义
包含用户、作文批改及相关数据模型
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin, user, premium
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 关系
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    essays = db.relationship('Essay', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, username, email, password, role='user'):
        self.username = username
        self.email = email
        self.set_password(password)
        self.role = role
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        """是否已认证"""
        return True
    
    def is_premium(self):
        """是否为高级用户"""
        return self.role == 'premium' or self.role == 'admin'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserProfile(db.Model):
    """用户档案"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100))
    school = db.Column(db.String(100))
    grade = db.Column(db.String(20))
    subscription_expires = db.Column(db.DateTime)
    essay_count = db.Column(db.Integer, default=0)
    essay_monthly_limit = db.Column(db.Integer, default=5)
    essay_monthly_used = db.Column(db.Integer, default=0)
    reset_date = db.Column(db.DateTime)
    
    def update_essay_count(self):
        """更新作文数量"""
        self.essay_count += 1
        self.essay_monthly_used += 1
    
    def is_limit_reached(self):
        """检查是否达到月度限制"""
        if self.subscription_expires and self.subscription_expires > datetime.utcnow():
            return False  # 订阅用户无限制
        
        now = datetime.utcnow()
        if not self.reset_date or now.month != self.reset_date.month:
            # 新的月份，重置计数
            self.essay_monthly_used = 0
            self.reset_date = now
            return False
        
        return self.essay_monthly_used >= self.essay_monthly_limit
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'school': self.school,
            'grade': self.grade,
            'subscription_expires': self.subscription_expires.strftime('%Y-%m-%d %H:%M:%S') if self.subscription_expires else None,
            'essay_count': self.essay_count,
            'essay_monthly_limit': self.essay_monthly_limit,
            'essay_monthly_used': self.essay_monthly_used,
            'reset_date': self.reset_date.strftime('%Y-%m-%d') if self.reset_date else None
        }

class Essay(db.Model):
    """作文模型"""
    __tablename__ = 'essays'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    corrected_text = db.Column(db.Text)
    word_count = db.Column(db.Integer)
    submission_time = db.Column(db.DateTime, default=datetime.utcnow)
    processed_time = db.Column(db.Float)  # 处理时间（秒）
    grade = db.Column(db.String(20))  # 作文等级：优、良、中、差
    
    # 异步处理相关字段
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    task_id = db.Column(db.String(50))  # Celery任务ID
    error_message = db.Column(db.Text)  # 处理失败时的错误信息
    
    # 评分和反馈（JSON格式）
    scores_json = db.Column(db.Text)  # 包含总分和各项分数
    feedback_json = db.Column(db.Text)  # 包含总体评价和各项评价
    errors_json = db.Column(db.Text)  # 包含错误列表
    suggestions_json = db.Column(db.Text)  # 改进建议列表
    
    @property
    def scores(self):
        """获取评分字典"""
        if not self.scores_json:
            return {}
        return json.loads(self.scores_json)
    
    @scores.setter
    def scores(self, value):
        """设置评分字典"""
        self.scores_json = json.dumps(value)
    
    @property
    def feedback(self):
        """获取反馈字典"""
        if not self.feedback_json:
            return {}
        return json.loads(self.feedback_json)
    
    @feedback.setter
    def feedback(self, value):
        """设置反馈字典"""
        self.feedback_json = json.dumps(value)
    
    @property
    def errors(self):
        """获取错误列表"""
        if not self.errors_json:
            return []
        return json.loads(self.errors_json)
    
    @errors.setter
    def errors(self, value):
        """设置错误列表"""
        self.errors_json = json.dumps(value)
    
    @property
    def suggestions(self):
        """获取建议列表"""
        if not self.suggestions_json:
            return []
        return json.loads(self.suggestions_json)
    
    @suggestions.setter
    def suggestions(self, value):
        """设置建议列表"""
        self.suggestions_json = json.dumps(value)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'essay_id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'original_text': self.original_text,
            'corrected_text': self.corrected_text,
            'word_count': self.word_count,
            'submission_time': self.submission_time.strftime('%Y-%m-%d %H:%M:%S'),
            'processed_time': self.processed_time,
            'grade': self.grade,
            'status': self.status,
            'score': self.scores,
            'feedback': self.feedback,
            'errors': self.errors,
            'improvement_suggestions': self.suggestions
        }
    
    def to_list_dict(self):
        """转换为列表展示用的字典（简化版）"""
        return {
            'essay_id': self.id,
            'title': self.title,
            'submission_time': self.submission_time.strftime('%Y-%m-%d %H:%M:%S'),
            'grade': self.grade,
            'word_count': self.word_count,
            'status': self.status,
            'total_score': self.scores.get('total', 0) if self.scores else 0
        }
    
    def is_completed(self):
        """检查作文是否已完成批改"""
        return self.status == 'completed'
    
    def is_processing(self):
        """检查作文是否正在处理中"""
        return self.status == 'processing'
    
    def is_failed(self):
        """检查作文是否处理失败"""
        return self.status == 'failed'
    
    def is_pending(self):
        """检查作文是否等待处理"""
        return self.status == 'pending'

# 迁移到以下表可以按需使用

class Subscription(db.Model):
    """订阅模型"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan = db.Column(db.String(20), nullable=False)  # 'monthly', 'yearly'
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    payment_id = db.Column(db.String(100))
    
    # 关系
    user = db.relationship('User', backref=db.backref('subscriptions', lazy='dynamic'))

class LoginHistory(db.Model):
    """登录历史"""
    __tablename__ = 'login_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # 关系
    user = db.relationship('User', backref=db.backref('login_history', lazy='dynamic'))
