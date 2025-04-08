#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
支付服务模块
处理支付流程和支付网关集成
"""

import logging
import datetime
import json
import uuid
import time
import hashlib
import hmac
import base64
import requests
from typing import Dict, Any, List, Optional, Tuple

from app.config import config
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.db import db

logger = logging.getLogger(__name__)

class PaymentGateway:
    """支付网关基类"""
    
    def __init__(self, config_dict):
        """初始化支付网关"""
        self.config = config_dict
    
    def create_payment(self, order_id, amount, subject, description=None, **kwargs):
        """创建支付订单"""
        raise NotImplementedError("子类必须实现create_payment方法")
    
    def verify_payment(self, payment_data):
        """验证支付结果"""
        raise NotImplementedError("子类必须实现verify_payment方法")
    
    def query_payment(self, order_id):
        """查询支付状态"""
        raise NotImplementedError("子类必须实现query_payment方法")

class AlipayGateway(PaymentGateway):
    """支付宝支付网关"""
    
    def create_payment(self, order_id, amount, subject, description=None, **kwargs):
        """
        创建支付宝支付订单
        
        Args:
            order_id: 订单ID
            amount: 支付金额
            subject: 订单标题
            description: 订单描述
            
        Returns:
            Dict: 支付创建结果
        """
        try:
            # 注意：这里只是示例，实际实现需要根据支付宝API文档完成
            logger.info(f"创建支付宝支付订单: order_id={order_id}, amount={amount}, subject={subject}")
            
            # 构建支付宝请求参数
            biz_content = {
                "out_trade_no": order_id,
                "total_amount": str(amount),
                "subject": subject,
                "product_code": "FAST_INSTANT_TRADE_PAY"
            }
            
            if description:
                biz_content["body"] = description
                
            # 这里是模拟，实际需要调用支付宝API
            payment_url = "https://openapi.alipay.com/gateway.do?mock=true"
            
            return {
                "status": "success",
                "payment_url": payment_url,
                "order_id": order_id,
                "gateway": "alipay"
            }
            
        except Exception as e:
            logger.error(f"创建支付宝支付订单失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"创建支付失败: {str(e)}"
            }
    
    def verify_payment(self, payment_data):
        """
        验证支付宝支付结果
        
        Args:
            payment_data: 支付回调数据
            
        Returns:
            Dict: 验证结果
        """
        try:
            # 注意：这里只是示例，实际实现需要根据支付宝API文档完成
            logger.info(f"验证支付宝支付结果: {payment_data}")
            
            # 验证签名等
            # ...
            
            # 提取订单号和交易状态
            order_id = payment_data.get("out_trade_no")
            trade_status = payment_data.get("trade_status")
            
            if not order_id or not trade_status:
                return {
                    "status": "error",
                    "message": "缺少必要的参数"
                }
            
            # 判断交易状态
            if trade_status == "TRADE_SUCCESS":
                return {
                    "status": "success",
                    "order_id": order_id,
                    "transaction_id": payment_data.get("trade_no"),
                    "amount": float(payment_data.get("total_amount", 0)),
                    "payment_time": datetime.datetime.now()
                }
            else:
                return {
                    "status": "pending",
                    "message": f"支付未完成，状态: {trade_status}",
                    "order_id": order_id
                }
                
        except Exception as e:
            logger.error(f"验证支付宝支付结果失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"验证支付失败: {str(e)}"
            }
    
    def query_payment(self, order_id):
        """
        查询支付宝支付状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            Dict: 查询结果
        """
        try:
            # 注意：这里只是示例，实际实现需要根据支付宝API文档完成
            logger.info(f"查询支付宝支付状态: order_id={order_id}")
            
            # 这里是模拟，实际需要调用支付宝API
            # 随机返回支付状态，实际应该调用支付宝接口查询
            import random
            status = random.choice(["WAIT_BUYER_PAY", "TRADE_SUCCESS", "TRADE_CLOSED"])
            
            if status == "TRADE_SUCCESS":
                return {
                    "status": "success",
                    "order_id": order_id,
                    "transaction_id": f"2023{order_id}",
                    "amount": 0,  # 实际应从查询结果中获取
                    "payment_time": datetime.datetime.now()
                }
            elif status == "WAIT_BUYER_PAY":
                return {
                    "status": "pending",
                    "message": "等待支付",
                    "order_id": order_id
                }
            else:
                return {
                    "status": "failed",
                    "message": "支付已关闭",
                    "order_id": order_id
                }
                
        except Exception as e:
            logger.error(f"查询支付宝支付状态失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"查询支付失败: {str(e)}"
            }

class WechatPayGateway(PaymentGateway):
    """微信支付网关"""
    
    def create_payment(self, order_id, amount, subject, description=None, **kwargs):
        """
        创建微信支付订单
        
        Args:
            order_id: 订单ID
            amount: 支付金额（单位：元）
            subject: 订单标题
            description: 订单描述
            
        Returns:
            Dict: 支付创建结果
        """
        try:
            # 注意：这里只是示例，实际实现需要根据微信支付API文档完成
            logger.info(f"创建微信支付订单: order_id={order_id}, amount={amount}, subject={subject}")
            
            # 将金额转换为分
            amount_in_cents = int(amount * 100)
            
            # 构建微信支付请求参数
            # 实际开发中需要生成签名等
            biz_content = {
                "out_trade_no": order_id,
                "total_fee": amount_in_cents,
                "body": subject,
                "trade_type": "JSAPI"  # 或NATIVE、APP等
            }
            
            if description:
                biz_content["detail"] = description
                
            # 这里是模拟，实际需要调用微信支付API
            
            # 生成一个二维码链接（实际应调用微信接口获取）
            if kwargs.get("trade_type") == "NATIVE":
                code_url = f"weixin://wxpay/bizpayurl?pr={order_id}"
                return {
                    "status": "success",
                    "code_url": code_url,
                    "order_id": order_id,
                    "gateway": "wechat"
                }
            else:
                # 返回JSAPI支付需要的参数
                return {
                    "status": "success",
                    "prepay_id": f"wx{int(time.time())}",
                    "order_id": order_id,
                    "gateway": "wechat"
                }
            
        except Exception as e:
            logger.error(f"创建微信支付订单失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"创建支付失败: {str(e)}"
            }
    
    def verify_payment(self, payment_data):
        """
        验证微信支付结果
        
        Args:
            payment_data: 支付回调数据
            
        Returns:
            Dict: 验证结果
        """
        try:
            # 注意：这里只是示例，实际实现需要根据微信支付API文档完成
            logger.info(f"验证微信支付结果: {payment_data}")
            
            # 验证签名等
            # ...
            
            # 提取订单号和交易状态
            order_id = payment_data.get("out_trade_no")
            result_code = payment_data.get("result_code")
            
            if not order_id or not result_code:
                return {
                    "status": "error",
                    "message": "缺少必要的参数"
                }
            
            # 判断交易状态
            if result_code == "SUCCESS":
                return {
                    "status": "success",
                    "order_id": order_id,
                    "transaction_id": payment_data.get("transaction_id"),
                    "amount": float(payment_data.get("total_fee", 0)) / 100,  # 分转元
                    "payment_time": datetime.datetime.now()
                }
            else:
                return {
                    "status": "failed",
                    "message": f"支付失败，错误码: {payment_data.get('err_code')}",
                    "order_id": order_id
                }
                
        except Exception as e:
            logger.error(f"验证微信支付结果失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"验证支付失败: {str(e)}"
            }
    
    def query_payment(self, order_id):
        """
        查询微信支付状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            Dict: 查询结果
        """
        try:
            # 注意：这里只是示例，实际实现需要根据微信支付API文档完成
            logger.info(f"查询微信支付状态: order_id={order_id}")
            
            # 这里是模拟，实际需要调用微信支付API
            # 随机返回支付状态，实际应该调用微信接口查询
            import random
            status = random.choice(["NOTPAY", "SUCCESS", "CLOSED"])
            
            if status == "SUCCESS":
                return {
                    "status": "success",
                    "order_id": order_id,
                    "transaction_id": f"4200001{order_id}",
                    "amount": 0,  # 实际应从查询结果中获取
                    "payment_time": datetime.datetime.now()
                }
            elif status == "NOTPAY":
                return {
                    "status": "pending",
                    "message": "等待支付",
                    "order_id": order_id
                }
            else:
                return {
                    "status": "failed",
                    "message": "支付已关闭",
                    "order_id": order_id
                }
                
        except Exception as e:
            logger.error(f"查询微信支付状态失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"查询支付失败: {str(e)}"
            }

class PaymentService:
    """支付服务类，处理支付流程和支付网关集成"""
    
    def __init__(self):
        """初始化支付服务"""
        self.payment_gateways = {}
        
        # 加载支付配置
        payment_config = config.PAYMENT_CONFIG
        
        # 初始化支付网关
        if payment_config.get("alipay", {}).get("enabled", False):
            self.payment_gateways["alipay"] = AlipayGateway(payment_config.get("alipay", {}))
            
        if payment_config.get("wechat", {}).get("enabled", False):
            self.payment_gateways["wechat"] = WechatPayGateway(payment_config.get("wechat", {}))
    
    def create_payment(self, subscription_id: int, payment_method: str) -> Dict[str, Any]:
        """
        创建支付订单
        
        Args:
            subscription_id: 订阅ID
            payment_method: 支付方式（alipay/wechat）
        
        Returns:
            Dict: 支付创建结果
        """
        try:
            # 验证支付方式
            if payment_method not in self.payment_gateways:
                return {
                    "status": "error",
                    "message": f"不支持的支付方式: {payment_method}"
                }
            
            # 获取订阅信息
            subscription = Subscription.query.get(subscription_id)
            if not subscription:
                return {
                    "status": "error",
                    "message": "订阅不存在"
                }
            
            # 检查订阅状态
            if subscription.status not in [SubscriptionStatus.PENDING.value, SubscriptionStatus.EXPIRED.value]:
                return {
                    "status": "error",
                    "message": f"订阅状态为{subscription.status}，无法创建支付"
                }
            
            # 生成订单ID
            order_id = f"{int(time.time())}{subscription_id}"
            
            # 创建支付记录
            payment = Payment(
                user_id=subscription.user_id,
                subscription_id=subscription_id,
                amount=subscription.price,
                currency="CNY",
                payment_method=payment_method,
                status=PaymentStatus.PENDING.value,
                order_id=order_id
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # 调用支付网关创建支付
            gateway = self.payment_gateways[payment_method]
            
            # 构建支付信息
            subject = f"会员订阅-{subscription.plan_id}"
            description = f"购买{subscription.duration}会员"
            
            # 创建支付
            result = gateway.create_payment(
                order_id=order_id,
                amount=subscription.price,
                subject=subject,
                description=description
            )
            
            # 处理结果
            if result.get("status") == "success":
                # 更新支付记录
                payment.payment_data = json.dumps(result)
                db.session.commit()
                
                return {
                    "status": "success",
                    "payment_id": payment.id,
                    "order_id": order_id,
                    "amount": subscription.price,
                    "currency": "CNY",
                    "payment_method": payment_method,
                    "payment_url": result.get("payment_url"),
                    "code_url": result.get("code_url"),
                    "prepay_id": result.get("prepay_id")
                }
            else:
                # 支付创建失败
                payment.status = PaymentStatus.FAILED.value
                payment.notes = result.get("message")
                db.session.commit()
                
                return result
            
        except Exception as e:
            logger.error(f"创建支付订单时发生错误: {str(e)}", exc_info=True)
            if 'db' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"创建支付订单时发生错误: {str(e)}"
            }
    
    def process_payment_callback(self, payment_method: str, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理支付回调
        
        Args:
            payment_method: 支付方式
            callback_data: 回调数据
        
        Returns:
            Dict: 处理结果
        """
        try:
            # 验证支付方式
            if payment_method not in self.payment_gateways:
                return {
                    "status": "error",
                    "message": f"不支持的支付方式: {payment_method}"
                }
            
            # 调用支付网关验证回调
            gateway = self.payment_gateways[payment_method]
            result = gateway.verify_payment(callback_data)
            
            if result.get("status") != "success":
                return result
            
            # 获取订单ID
            order_id = result.get("order_id")
            
            # 查找支付记录
            payment = Payment.query.filter_by(order_id=order_id).first()
            if not payment:
                logger.warning(f"支付回调找不到对应的支付记录: order_id={order_id}")
                return {
                    "status": "error",
                    "message": "找不到对应的支付记录"
                }
            
            # 检查支付状态，避免重复处理
            if payment.status == PaymentStatus.SUCCESS.value:
                logger.info(f"支付已经处理过: order_id={order_id}")
                return {
                    "status": "success",
                    "message": "支付已处理",
                    "payment_id": payment.id
                }
            
            # 更新支付记录
            payment.status = PaymentStatus.SUCCESS.value
            payment.transaction_id = result.get("transaction_id")
            payment.payment_time = result.get("payment_time")
            payment.payment_data = json.dumps(callback_data)
            
            # 更新订阅状态
            subscription = Subscription.query.get(payment.subscription_id)
            if subscription:
                subscription.status = SubscriptionStatus.ACTIVE.value
                subscription.updated_at = datetime.datetime.now()
            
            db.session.commit()
            
            # 返回处理结果
            return {
                "status": "success",
                "message": "支付回调处理成功",
                "payment_id": payment.id,
                "subscription_id": payment.subscription_id
            }
            
        except Exception as e:
            logger.error(f"处理支付回调时发生错误: {str(e)}", exc_info=True)
            if 'db' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"处理支付回调时发生错误: {str(e)}"
            }
    
    def query_payment_status(self, payment_id: int) -> Dict[str, Any]:
        """
        查询支付状态
        
        Args:
            payment_id: 支付ID
        
        Returns:
            Dict: 查询结果
        """
        try:
            # 获取支付记录
            payment = Payment.query.get(payment_id)
            if not payment:
                return {
                    "status": "error",
                    "message": "支付记录不存在"
                }
            
            # 如果支付已成功，直接返回
            if payment.status == PaymentStatus.SUCCESS.value:
                return {
                    "status": "success",
                    "payment": {
                        "id": payment.id,
                        "order_id": payment.order_id,
                        "amount": payment.amount,
                        "payment_method": payment.payment_method,
                        "status": payment.status,
                        "payment_time": payment.payment_time.isoformat() if payment.payment_time else None,
                        "transaction_id": payment.transaction_id
                    }
                }
            
            # 调用支付网关查询支付状态
            if payment.payment_method in self.payment_gateways:
                gateway = self.payment_gateways[payment.payment_method]
                result = gateway.query_payment(payment.order_id)
                
                # 如果查询成功且支付成功，更新支付记录
                if result.get("status") == "success":
                    payment.status = PaymentStatus.SUCCESS.value
                    payment.transaction_id = result.get("transaction_id")
                    payment.payment_time = result.get("payment_time") or datetime.datetime.now()
                    
                    # 更新订阅状态
                    subscription = Subscription.query.get(payment.subscription_id)
                    if subscription:
                        subscription.status = SubscriptionStatus.ACTIVE.value
                        subscription.updated_at = datetime.datetime.now()
                    
                    db.session.commit()
                elif result.get("status") == "failed":
                    payment.status = PaymentStatus.FAILED.value
                    payment.notes = result.get("message")
                    db.session.commit()
                
                # 构建返回结果
                return {
                    "status": result.get("status"),
                    "message": result.get("message", ""),
                    "payment": {
                        "id": payment.id,
                        "order_id": payment.order_id,
                        "amount": payment.amount,
                        "payment_method": payment.payment_method,
                        "status": payment.status,
                        "payment_time": payment.payment_time.isoformat() if payment.payment_time else None,
                        "transaction_id": payment.transaction_id
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"不支持的支付方式: {payment.payment_method}"
                }
                
        except Exception as e:
            logger.error(f"查询支付状态时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"查询支付状态时发生错误: {str(e)}"
            }
    
    def cancel_payment(self, payment_id: int) -> Dict[str, Any]:
        """
        取消支付
        
        Args:
            payment_id: 支付ID
        
        Returns:
            Dict: 取消结果
        """
        try:
            # 获取支付记录
            payment = Payment.query.get(payment_id)
            if not payment:
                return {
                    "status": "error",
                    "message": "支付记录不存在"
                }
            
            # 检查支付状态
            if payment.status != PaymentStatus.PENDING.value:
                return {
                    "status": "error",
                    "message": f"支付状态为{payment.status}，无法取消"
                }
            
            # 更新支付状态
            payment.status = PaymentStatus.CANCELED.value
            payment.updated_at = datetime.datetime.now()
            
            db.session.commit()
            
            return {
                "status": "success",
                "message": "支付已取消",
                "payment_id": payment.id
            }
            
        except Exception as e:
            logger.error(f"取消支付时发生错误: {str(e)}", exc_info=True)
            if 'db' in locals():
                db.session.rollback()
            return {
                "status": "error",
                "message": f"取消支付时发生错误: {str(e)}"
            }
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """
        获取支持的支付方式
        
        Returns:
            Dict: 支付方式列表
        """
        try:
            methods = []
            
            for method_name in self.payment_gateways.keys():
                methods.append({
                    "code": method_name,
                    "name": self._get_payment_method_name(method_name),
                    "icon": self._get_payment_method_icon(method_name)
                })
            
            return {
                "status": "success",
                "methods": methods
            }
            
        except Exception as e:
            logger.error(f"获取支付方式时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"获取支付方式时发生错误: {str(e)}"
            }
    
    def _get_payment_method_name(self, method_code: str) -> str:
        """获取支付方式名称"""
        names = {
            "alipay": "支付宝",
            "wechat": "微信支付"
        }
        return names.get(method_code, method_code)
    
    def _get_payment_method_icon(self, method_code: str) -> str:
        """获取支付方式图标URL"""
        icons = {
            "alipay": "/static/images/payment/alipay.png",
            "wechat": "/static/images/payment/wechat.png"
        }
        return icons.get(method_code, "") 