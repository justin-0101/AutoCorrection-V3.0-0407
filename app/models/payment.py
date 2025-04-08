#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
支付相关数据模型
定义支付记录和相关信息
"""

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

# from app.db.database import Base
from app.models.db import db, BaseModel


class PaymentStatus(enum.Enum):
    """支付状态枚举"""
    PENDING = "pending"  # 待支付
    SUCCESS = "success"  # 支付成功
    FAILED = "failed"    # 支付失败
    CANCELED = "canceled"  # 已取消
    REFUNDED = "refunded"  # 已退款


class PaymentMethod(enum.Enum):
    """支付方式枚举"""
    ALIPAY = "alipay"  # 支付宝
    WECHAT = "wechat"  # 微信支付
    CREDIT = "credit"  # 点数支付
    OTHER = "other"    # 其他方式


class Payment(BaseModel):
    """支付记录模型"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    
    # 支付信息
    order_id = Column(String(100), unique=True, nullable=False, index=True, comment="订单号")
    transaction_id = Column(String(100), nullable=True, comment="交易号")
    amount = Column(Float, nullable=False, comment="支付金额")
    currency = Column(String(10), nullable=False, default="CNY", comment="货币类型")
    
    # 支付状态
    status = Column(String(20), nullable=False, default=PaymentStatus.PENDING.value, comment="支付状态")
    payment_method = Column(String(50), nullable=False, comment="支付方式")
    payment_time = Column(DateTime, nullable=True, comment="支付时间")
    
    # 支付数据
    payment_data = Column(Text, nullable=True, comment="支付相关数据，JSON格式")
    notes = Column(String(255), nullable=True, comment="备注")
    error_message = Column(Text)  # 错误信息
    extra_data = Column(JSON)  # 额外的元数据
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment {self.id}: {self.order_id} - {self.amount} {self.currency} - {self.status}>"

    def to_dict(self):
        """将支付记录转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_id': self.order_id,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'status': self.status,
            'transaction_id': self.transaction_id,
            'error_message': self.error_message,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Invoice(BaseModel):
    """发票模型"""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 发票信息
    invoice_no = Column(String(64), unique=True, nullable=False, index=True, comment="发票号")
    title = Column(String(128), nullable=False, comment="发票抬头")
    tax_no = Column(String(64), nullable=True, comment="税号")
    amount = Column(Float, nullable=False, comment="发票金额")
    content = Column(String(128), nullable=False, comment="发票内容")
    
    # 状态信息
    status = Column(String(20), nullable=False, comment="发票状态")
    type = Column(String(20), nullable=False, comment="发票类型")  # 电子/纸质
    email = Column(String(128), nullable=True, comment="接收邮箱")
    address = Column(String(255), nullable=True, comment="邮寄地址")
    
    # 时间信息
    applied_at = Column(DateTime, nullable=False, default=datetime.now, comment="申请时间")
    issued_at = Column(DateTime, nullable=True, comment="开具时间")
    
    # 其他信息
    notes = Column(String(255), nullable=True, comment="备注")
    
    # 关联
    payment = relationship("Payment", backref="invoice")
    user = relationship("User", backref="invoices")
    
    def __repr__(self):
        return f"<Invoice {self.id}: {self.invoice_no} - {self.amount} - {self.status}>"


class Refund(BaseModel):
    """退款记录模型"""
    __tablename__ = "refunds"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 退款信息
    refund_no = Column(String(64), unique=True, nullable=False, index=True, comment="退款单号")
    amount = Column(Float, nullable=False, comment="退款金额")
    reason = Column(Text, nullable=False, comment="退款原因")
    
    # 退款状态
    status = Column(String(20), nullable=False, comment="退款状态")
    transaction_id = Column(String(100), nullable=True, comment="退款交易号")
    refund_time = Column(DateTime, nullable=True, comment="退款时间")
    error_message = Column(Text)  # 错误信息
    extra_data = Column(JSON)  # 额外的元数据
    
    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # 其他信息
    notes = Column(String(255), nullable=True, comment="备注")
    
    # 关联
    payment = relationship("Payment", backref="refunds")
    user = relationship("User", backref="refunds")
    
    def __repr__(self):
        return f"<Refund {self.id}: {self.refund_no} - {self.amount} - {self.status}>"

    def to_dict(self):
        """将退款记录转换为字典"""
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'amount': self.amount,
            'reason': self.reason,
            'status': self.status,
            'transaction_id': self.transaction_id,
            'error_message': self.error_message,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 