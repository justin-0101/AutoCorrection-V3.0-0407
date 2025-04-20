#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文相关数据模型
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON, Enum, event
from sqlalchemy.orm import relationship, validates
import logging

# 创建logger实例
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.models.db import db, BaseModel
from app.utils.input_sanitizer import sanitize_input, sanitize_enum_input
try:
    from app.core.monitoring import track_source_type
except ImportError:
    # 如果监控模块未加载，提供一个空函数
    def track_source_type(source_type):
        pass

# 删除直接从Correction导入的语句
# from app.models.correction import Correction, CorrectionStatus

class EssayStatus(str, enum.Enum):
    """作文状态枚举"""
    DRAFT = 'draft'           # 草稿
    PENDING = 'pending'       # 等待批改
    PROCESSING = 'processing' # 正在提交处理中（临时状态）
    CORRECTING = 'correcting' # 正在批改
    COMPLETED = 'completed'   # 批改完成
    FAILED = 'failed'          # 批改失败
    ARCHIVED = 'archived'     # 已归档

    @classmethod
    def get_display_text(cls, status):
        """获取状态的显示文本"""
        status_text = {
            cls.DRAFT.value: '草稿',
            cls.PENDING.value: '等待批改',
            cls.PROCESSING.value: '正在提交处理中',
            cls.CORRECTING.value: '正在批改中',
            cls.COMPLETED.value: '批改完成',
            cls.FAILED.value: '批改失败',
            cls.ARCHIVED.value: '已归档'
        }
        return status_text.get(status, '未知状态')

class EssaySourceType(enum.Enum):
    """作文来源类型枚举"""
    # 使用小写以保持与数据库值一致
    text = 'text'        # 默认文本类型
    upload = 'upload'    # 文件上传
    paste = 'paste'      # 文本粘贴
    api = 'api'          # API提交

    @property
    def display_name(self):
        """返回国际化的显示名称"""
        translation_map = {
            'text': '文本输入',
            'upload': '文件上传',
            'paste': '文本粘贴',
            'api': 'API提交'
        }
        return translation_map.get(self.value, self.value)

class Essay(BaseModel):
    """作文模型"""
    __tablename__ = 'essays'
    
    # 添加数据库级别约束
    __table_args__ = (
        db.CheckConstraint(
            "source_type IN ('text', 'paste', 'upload', 'api')",
            name='valid_source_type'
        ),
        db.CheckConstraint(
            "status IN ('draft', 'pending', 'processing', 'correcting', 'completed', 'failed', 'archived')",
            name='valid_status'
        ),
    )
    
    # 添加版本控制字段
    version = Column(Integer, default=0, nullable=False)
    
    # 基本信息
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    
    # 作者信息
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    author_name = Column(String(100))
    
    # 批改状态
    status = Column(String(20), default=EssayStatus.PENDING.value)
    score = Column(Float)
    corrected_at = Column(DateTime)
    error_message = Column(Text)  # 错误信息
    
    # 添加grade字段
    grade = Column(String(50), nullable=True, comment='作文年级水平')
    
    # 来源信息
    source_type = Column(String(20), default=EssaySourceType.text.value,
                     nullable=False, comment='内容来源类型')
    
    # 批改结果
    corrected_content = Column(Text)
    comments = Column(Text)
    error_analysis = Column(JSON)
    improvement_suggestions = Column(Text)
    
    # AI批改结果
    ai_score = Column(Float)
    ai_comments = Column(Text)
    ai_analysis = Column(JSON)
    
    # 统计信息
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    correction_count = Column(Integer, default=0)  # 批改次数
    
    # 元数据
    is_public = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系 - 使用字符串形式引用模型，避免循环导入
    user = relationship('User', back_populates='essays', lazy='joined')
    corrections = relationship('Correction', back_populates='essay',
                             lazy='dynamic', cascade='all, delete-orphan')
    feedbacks = relationship('UserFeedback', back_populates='essay',
                           lazy='dynamic', cascade='all, delete-orphan')
    
    @validates('status')
    def validate_status(self, key, value):
        """验证状态值"""
        if isinstance(value, EssayStatus):
            return value.value
        return sanitize_input(
            value,
            max_length=20,
            default=EssayStatus.PENDING.value,
            enum_values=[s.value for s in EssayStatus]
        )
    
    @validates('source_type')
    def validate_source_type(self, key, value):
        """验证source_type值"""
        if isinstance(value, EssaySourceType):
            return value.value
        return sanitize_input(
            value,
            max_length=20,
            default=EssaySourceType.text.value,
            enum_values=[t.value for t in EssaySourceType]
        )
    
    def update_status(self, new_status, error_message=None):
        """
        更新作文状态
        
        Args:
            new_status: 新状态
            error_message: 错误信息（可选）
            
        Returns:
            bool: 是否更新成功
        """
        # 如果传入的是枚举对象，获取它的值
        if isinstance(new_status, EssayStatus):
            new_status = new_status.value
            
        # 定义有效的状态转换
        valid_transitions = {
            EssayStatus.DRAFT.value: [EssayStatus.PENDING.value],
            EssayStatus.PENDING.value: [EssayStatus.PROCESSING.value, EssayStatus.CORRECTING.value, EssayStatus.FAILED.value],
            EssayStatus.PROCESSING.value: [EssayStatus.CORRECTING.value, EssayStatus.FAILED.value, EssayStatus.PENDING.value],
            EssayStatus.CORRECTING.value: [EssayStatus.COMPLETED.value, EssayStatus.FAILED.value],
            EssayStatus.COMPLETED.value: [EssayStatus.ARCHIVED.value],
            EssayStatus.FAILED.value: [EssayStatus.PENDING.value, EssayStatus.PROCESSING.value],
            EssayStatus.ARCHIVED.value: []
        }
        
        old_status = self.status
        
        # 检查状态转换是否有效
        if old_status not in valid_transitions:
            logger.warning(f"当前状态无效: {old_status}")
            return False
            
        if new_status not in valid_transitions[old_status]:
            logger.warning(f"状态转换无效: {old_status} -> {new_status}")
            return False
            
        try:
            # 更新状态
            self.status = new_status
            
            # 更新相关字段
            if new_status == EssayStatus.COMPLETED.value:
                self.corrected_at = datetime.utcnow()
            elif new_status == EssayStatus.FAILED.value:
                if error_message:
                    self.error_message = error_message
                    
            # 记录状态变更
            logger.info(f"作文 {self.id} 状态已更新: {old_status} -> {new_status}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新作文状态时出错: {str(e)}")
            return False
            
    def can_transition_to(self, target_status):
        """
        检查是否可以转换到目标状态
        
        Args:
            target_status: 目标状态
            
        Returns:
            bool: 是否可以转换
        """
        if isinstance(target_status, EssayStatus):
            target_status = target_status.value
            
        valid_transitions = {
            EssayStatus.DRAFT.value: [EssayStatus.PENDING.value],
            EssayStatus.PENDING.value: [EssayStatus.PROCESSING.value, EssayStatus.CORRECTING.value, EssayStatus.FAILED.value],
            EssayStatus.PROCESSING.value: [EssayStatus.CORRECTING.value, EssayStatus.FAILED.value, EssayStatus.PENDING.value],
            EssayStatus.CORRECTING.value: [EssayStatus.COMPLETED.value, EssayStatus.FAILED.value],
            EssayStatus.COMPLETED.value: [EssayStatus.ARCHIVED.value],
            EssayStatus.FAILED.value: [EssayStatus.PENDING.value, EssayStatus.PROCESSING.value],
            EssayStatus.ARCHIVED.value: []
        }
        
        return (self.status in valid_transitions and 
                target_status in valid_transitions[self.status])
    
    def get_latest_correction(self):
        """获取最新的批改记录"""
        # 使用字符串方式访问属性
        from app.models.correction import Correction
        return self.corrections.order_by(Correction.created_at.desc()).first()
    
    def sync_correction_results(self, correction):
        """
        同步批改结果到作文
        
        Args:
            correction: Correction对象
        
        Returns:
            bool: 是否成功同步
        """
        if not correction:
            return False
        
        try:
            if hasattr(correction, 'results') and correction.results:
                results = correction.results
                if isinstance(results, dict):
                    if 'score' in results:
                        self.score = results['score']
                    if 'corrected_content' in results:
                        self.corrected_content = results['corrected_content']
                    if 'comments' in results or 'overall_assessment' in results:
                        self.comments = results.get('comments') or results.get('overall_assessment')
                    if 'error_analysis' in results or 'spelling_errors' in results:
                        self.error_analysis = results.get('error_analysis') or results.get('spelling_errors')
                    if 'improvement_suggestions' in results:
                        self.improvement_suggestions = results['improvement_suggestions']
                
                # 更新批改完成时间
                self.corrected_at = datetime.utcnow()
                return True
        except Exception as e:
            logger.error(f"同步批改结果时出错: {str(e)}")
        
        return False
    
    def __init__(self, **kwargs):
        """初始化Essay对象"""
        # 处理source_type
        if 'source_type' in kwargs:
            kwargs['source_type'] = self.validate_source_type(None, kwargs['source_type'])
            
        # 处理status
        if 'status' in kwargs:
            kwargs['status'] = self.validate_status(None, kwargs['status'])
            
        # 调用父类的__init__
        super(Essay, self).__init__(**kwargs)
        
        # 计算词数
        if not self.word_count and self.content:
            self.word_count = len(self.content.split())
            
        # 监控指标
        try:
            track_source_type(self.source_type)
        except Exception:
            pass
    
    def __repr__(self):
        return f'<Essay {self.title}>'
    
    def to_dict(self):
        """将作文转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'word_count': self.word_count,
            'user_id': self.user_id,
            'author_name': self.author_name,
            'status': self.status,
            'status_display': EssayStatus.get_display_text(self.status),
            'score': self.score,
            'corrected_at': self.corrected_at.isoformat() if self.corrected_at else None,
            'error_message': self.error_message,
            'source_type': self.source_type,
            'source_type_display': EssaySourceType(self.source_type).display_name,
            'corrected_content': self.corrected_content,
            'comments': self.comments,
            'error_analysis': self.error_analysis,
            'improvement_suggestions': self.improvement_suggestions,
            'ai_score': self.ai_score,
            'ai_comments': self.ai_comments,
            'ai_analysis': self.ai_analysis,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'correction_count': self.correction_count,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def __declare_last__(cls):
        """在模型声明完成后设置事件监听器"""
        event.listen(cls, 'after_insert', cls._create_correction_record)
    
    @staticmethod
    def _create_correction_record(mapper, connection, target):
        """为新创建的Essay自动创建Correction记录"""
        # 只有当Essay状态为PENDING时才创建Correction记录
        if target.status != EssayStatus.PENDING.value:
            return

        # 使用原始SQL语句，避免循环依赖
        # 获取CorrectionStatus.PENDING值
        from app.models.correction import CorrectionStatus, CorrectionType
        pending_status = CorrectionStatus.PENDING.value
        ai_type = CorrectionType.AI.value

        try:
            # 插入Correction记录
            connection.execute(
                db.text(
                    """
                    INSERT INTO corrections 
                    (essay_id, type, status, version, created_at, updated_at, is_deleted) 
                    VALUES (:essay_id, :type, :status, 0, :created_at, :updated_at, 0)
                    """
                ),
                {
                    'essay_id': target.id,
                    'type': ai_type,
                    'status': pending_status,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            )
            logger.info(f"自动为Essay {target.id} 创建了Correction记录")
        except Exception as e:
            logger.error(f"为Essay {target.id} 创建Correction记录时出错: {str(e)}")

    def start_processing(self):
        """开始处理"""
        if self.status != EssayStatus.PENDING:
            raise ValueError(f"无法从{self.status}状态转换为处理中状态")
        self.status = EssayStatus.PROCESSING
        self.updated_at = datetime.now()
    
    def start_correcting(self):
        """开始批改"""
        if self.status != EssayStatus.PROCESSING:
            raise ValueError(f"无法从{self.status}状态转换为批改中状态")
        self.status = EssayStatus.CORRECTING
        self.updated_at = datetime.now()
    
    def complete(self):
        """完成批改"""
        if self.status not in [EssayStatus.PROCESSING, EssayStatus.CORRECTING]:
            raise ValueError(f"无法从{self.status}状态转换为已完成状态")
        self.status = EssayStatus.COMPLETED
        self.corrected_at = datetime.now()
        self.updated_at = datetime.now()
    
    def fail(self, error_message):
        """标记批改失败"""
        if self.status not in [EssayStatus.PROCESSING, EssayStatus.CORRECTING]:
            raise ValueError(f"无法从{self.status}状态转换为失败状态")
        self.status = EssayStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now()
        
    def archive(self):
        """归档作文"""
        if self.status == EssayStatus.ARCHIVED:
            raise ValueError("作文已经处于归档状态")
        self.status = EssayStatus.ARCHIVED
        self.updated_at = datetime.now()
        
    def optimistic_update(self, **kwargs):
        """
        乐观锁更新方法
        
        Args:
            **kwargs: 要更新的字段和值
            
        Returns:
            bool: 更新是否成功
            
        Raises:
            ConcurrentUpdateError: 当版本不匹配时抛出
        """
        try:
            current_version = self.version
            kwargs['version'] = current_version + 1
            
            # 使用版本号作为条件进行更新
            rows = db.session.query(Essay).filter(
                Essay.id == self.id,
                Essay.version == current_version
            ).update(kwargs)
            
            if rows == 0:
                db.session.rollback()
                from app.utils.exceptions import ConcurrentUpdateError
                raise ConcurrentUpdateError("数据已被其他进程修改")
            
            # 更新成功，同步当前对象的版本号
            self.version = current_version + 1
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            from app.utils.exceptions import DatabaseError
            raise DatabaseError(f"数据库更新失败: {str(e)}")
    
    def safe_update_status(self, new_status: str) -> bool:
        """
        安全地更新作文状态
        
        Args:
            new_status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            return self.optimistic_update(
                status=new_status,
                updated_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"作文状态更新冲突 [id={self.id}, status={new_status}]: {str(e)}")
            return False

class UserFeedback(BaseModel):
    """用户反馈模型"""
    __tablename__ = 'user_feedbacks'
    
    essay_id = Column(Integer, ForeignKey('essays.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    rating = Column(Integer)  # 1-5星评分
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    essay = relationship('Essay', back_populates='feedbacks')
    user = relationship('User', back_populates='feedbacks')
    
    def __repr__(self):
        return f'<UserFeedback for essay_id={self.essay_id}>'

class EssayTemplate(BaseModel):
    """作文模板模型"""
    __tablename__ = 'essay_templates'
    
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50))  # 分类：高考、四级、六级等
    difficulty = Column(String(20))  # 难度：简单、中等、困难
    word_count = Column(Integer)
    created_by = Column(Integer, ForeignKey('users.id'))
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<EssayTemplate {self.title}>'

class CorrectionRule(BaseModel):
    """批改规则模型"""
    __tablename__ = 'correction_rules'
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # 语法、词汇、结构等
    severity = Column(String(20))  # 严重程度：低、中、高
    points_deduction = Column(Float)  # 扣分
    created_by = Column(Integer, ForeignKey('users.id'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<CorrectionRule {self.name}>' 