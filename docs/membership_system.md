# 会员系统设计

## 1. 概述

会员系统是作文批改平台的核心功能模块之一，提供用户订阅、权限管理和特权功能。本文档详细描述了会员系统的设计、数据模型和功能实现。

## 2. 数据模型

### 2.1 会员订阅模型

```python
class Subscription(db.Model):
    """会员订阅模型"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.String(50), nullable=False)  # 订阅计划ID
    status = db.Column(db.String(20), default='active')  # active, canceled, expired
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    payment_id = db.Column(db.String(100))  # 支付系统的交易ID
    auto_renew = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    payments = db.relationship('Payment', backref='subscription', lazy='dynamic')
    
    def is_active(self):
        """检查订阅是否有效"""
        return (self.status == 'active' and 
                self.end_date > datetime.utcnow())
```

### 2.2 支付记录模型

```python
class Payment(db.Model):
    """支付记录模型"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='CNY')
    payment_method = db.Column(db.String(50))  # alipay, wechat, etc.
    transaction_id = db.Column(db.String(100))  # 支付平台交易ID
    status = db.Column(db.String(20))  # success, pending, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 2.3 会员套餐模型

```python
class MembershipPlan(db.Model):
    """会员套餐模型"""
    __tablename__ = 'membership_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, default=30)
    essay_limit = db.Column(db.Integer, default=10)  # 每月批改次数
    features = db.Column(db.Text)  # JSON格式的特权列表
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## 3. API接口设计

### 3.1 获取会员套餐接口

**请求**
```
GET /api/membership/plans
```

**响应**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "月度标准版",
      "code": "monthly_standard",
      "price": 29.99,
      "duration_days": 30,
      "essay_limit": 10,
      "features": ["基础批改", "详细评语", "错误分析"]
    },
    {
      "id": 2,
      "name": "季度高级版",
      "code": "quarterly_premium",
      "price": 79.99,
      "duration_days": 90,
      "essay_limit": 15,
      "features": ["高级批改", "详细评语", "错误分析", "学习建议", "进步追踪"]
    }
  ]
}
```

### 3.2 订阅会员套餐接口

**请求**
```
POST /api/membership/subscribe
```

**请求参数**
```json
{
  "plan_id": "monthly_standard",
  "payment_method": "alipay"
}
```

**响应**
```json
{
  "status": "success",
  "data": {
    "order_id": "ORD123456789",
    "payment_url": "https://example.com/pay?id=ORD123456789",
    "task_id": "task-id-123456"
  }
}
```

### 3.3 获取用户订阅信息接口

**请求**
```
GET /api/membership/subscription
```

**响应**
```json
{
  "status": "success",
  "data": {
    "subscription": {
      "plan_id": "monthly_standard",
      "status": "active",
      "start_date": "2023-04-01T00:00:00Z",
      "end_date": "2023-05-01T00:00:00Z",
      "auto_renew": false
    },
    "essay_limit": 10,
    "essays_used": 3,
    "essays_remaining": 7
  }
}
```

### 3.4 取消订阅接口

**请求**
```
POST /api/membership/cancel
```

**响应**
```json
{
  "status": "success",
  "message": "订阅已取消，您可以继续使用服务至订阅结束日期",
  "data": {
    "end_date": "2023-05-01T00:00:00Z"
  }
}
```

## 4. 异步任务处理

```python
@shared_task(name='tasks.membership_tasks.process_subscription')
def process_subscription(user_id, payment_id, plan_id, amount):
    """
    处理用户订阅
    
    Args:
        user_id: 用户ID
        payment_id: 支付ID
        plan_id: 订阅计划ID
        amount: 支付金额
    """
    try:
        from services.payment_service import PaymentService
        
        logger.info(f"开始处理用户订阅，用户ID: {user_id}, 支付ID: {payment_id}")
        
        # 验证支付状态
        payment_service = PaymentService()
        payment_status = payment_service.verify_payment(payment_id)
        
        if payment_status.get('status') != 'success':
            logger.warning(f"支付验证失败，用户ID: {user_id}, 支付ID: {payment_id}")
            return {
                "status": "error",
                "message": "支付验证失败",
                "payment_status": payment_status
            }
        
        # 获取订阅计划详情
        plan_details = payment_service.get_plan_details(plan_id)
        duration_days = plan_details.get('duration_days', 30)
        essay_limit = plan_details.get('essay_limit', 5)
        
        # 更新用户订阅
        with db.session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            
            if profile:
                # 计算新的到期日期
                from datetime import datetime, timedelta
                
                if profile.subscription_expires and profile.subscription_expires > datetime.now():
                    # 在现有订阅上延长
                    profile.subscription_expires += timedelta(days=duration_days)
                else:
                    # 新订阅
                    profile.subscription_expires = datetime.now() + timedelta(days=duration_days)
                
                # 更新作文限额
                profile.essay_monthly_limit = essay_limit
                profile.essay_monthly_used = 0
                
                session.commit()
                
                # 发送订阅成功通知
                notify_user(user_id, {
                    "type": "subscription_updated",
                    "subscription": {
                        "expires": profile.subscription_expires.isoformat(),
                        "plan": plan_id,
                        "essay_limit": essay_limit
                    }
                })
                
                logger.info(f"用户订阅更新成功，用户ID: {user_id}, 到期日期: {profile.subscription_expires}")
                
                return {
                    "status": "success",
                    "message": "订阅更新成功",
                    "subscription_expires": profile.subscription_expires.isoformat(),
                    "essay_limit": essay_limit
                }
            else:
                logger.error(f"用户资料不存在，用户ID: {user_id}")
                return {"status": "error", "message": "用户资料不存在"}
    
    except Exception as e:
        logger.error(f"处理用户订阅失败，用户ID: {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
```

## 5. 会员权限管理

### 5.1 权限检查装饰器

```python
def membership_required(essay_action=False):
    """
    会员权限检查装饰器
    
    Args:
        essay_action: 是否是作文相关操作（需要检查作文数量限制）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 验证用户登录
            if not hasattr(g, 'user') or not g.user.is_authenticated():
                return jsonify({
                    "status": "error",
                    "message": "请先登录",
                    "code": "login_required"
                }), 401
            
            # 检查会员权限
            user_profile = UserProfile.query.filter_by(user_id=g.user.id).first()
            
            # 管理员跳过检查
            if g.user.role == 'admin':
                return f(*args, **kwargs)
                
            # 非会员用户检查
            if not user_profile or not user_profile.subscription_expires or user_profile.subscription_expires < datetime.now():
                return jsonify({
                    "status": "error",
                    "message": "此功能需要会员权限",
                    "code": "membership_required"
                }), 403
            
            # 会员用户检查作文数量限制
            if essay_action and user_profile.is_limit_reached():
                return jsonify({
                    "status": "error",
                    "message": "您本月的作文批改次数已达上限",
                    "code": "essay_limit_reached",
                    "data": {
                        "limit": user_profile.essay_monthly_limit,
                        "used": user_profile.essay_monthly_used
                    }
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### 5.2 会员功能限制

```python
# 在作文批改接口中使用会员权限检查
@correction_bp.route('/submit', methods=['POST'])
@membership_required(essay_action=True)
def submit_essay():
    """提交作文进行批改"""
    # 实现代码...
```

## 6. 支付集成

### 6.1 支付服务

```python
# services/payment_service.py
class PaymentService:
    """支付服务"""
    
    def __init__(self):
        self.api_key = os.environ.get('PAYMENT_API_KEY')
        self.api_base_url = os.environ.get('PAYMENT_API_URL')
        self.merchant_id = os.environ.get('PAYMENT_MERCHANT_ID')
    
    def create_payment_order(self, user_id, plan_id, amount, payment_method):
        """创建支付订单"""
        # 支付平台API集成...
        
    def verify_payment(self, payment_id):
        """验证支付状态"""
        # 支付平台API集成...
        
    def get_plan_details(self, plan_id):
        """获取套餐详情"""
        plan = MembershipPlan.query.filter_by(code=plan_id).first()
        if not plan:
            return {}
        
        return {
            "id": plan.id,
            "name": plan.name,
            "price": plan.price,
            "duration_days": plan.duration_days,
            "essay_limit": plan.essay_limit,
            "features": json.loads(plan.features) if plan.features else []
        }
```

## 7. 用户界面设计

### 7.1 会员中心页面

会员中心页面包含以下内容：

1. 当前订阅状态
2. 订阅到期日期
3. 本月剩余作文批改次数
4. 订阅续费/升级选项
5. 历史支付记录
6. 自动续费设置

### 7.2 订阅页面

订阅页面展示所有可用的会员套餐，包括：

1. 套餐名称和描述
2. 价格和时长
3. 包含的特权和功能
4. 作文批改次数限制
5. 支付方式选择

## 8. 实时通知

会员系统通过WebSocket提供以下实时通知：

1. 订阅成功通知
2. 订阅即将到期提醒
3. 作文批改次数不足提醒
4. 自动续费成功/失败通知

## 9. 管理功能

后台管理系统提供以下会员管理功能：

1. 查看所有会员和订阅状态
2. 手动管理会员订阅(延长/取消)
3. 创建和管理会员套餐
4. 查看支付记录和统计数据
5. 配置会员权限和特权 