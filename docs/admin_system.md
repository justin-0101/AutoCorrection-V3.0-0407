# 后台管理系统设计

## 1. 概述

后台管理系统是作文批改平台的核心管理模块，提供用户管理、作文批改管理、数据统计和系统配置等功能。本文档详细描述了后台管理系统的设计和功能实现。

## 2. 系统架构

后台管理系统采用前后端分离架构：
- 后端：Flask API提供数据接口
- 前端：基于Bootstrap和Vue.js的管理界面
- 权限：基于角色的访问控制(RBAC)

## 3. 权限模型

### 3.1 角色定义

```python
# 角色常量
ROLE_ADMIN = 'admin'       # 系统管理员
ROLE_OPERATOR = 'operator' # 运营人员
ROLE_TEACHER = 'teacher'   # 教师
ROLE_USER = 'user'         # 普通用户

class Role(db.Model):
    """用户角色模型"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    permissions = db.Column(db.Integer, default=0)
    description = db.Column(db.String(255))
    
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    # 权限常量
    CORRECTION_VIEW = 0x01     # 查看作文
    CORRECTION_EDIT = 0x02     # 编辑作文评语
    USER_VIEW = 0x04           # 查看用户
    USER_EDIT = 0x08           # 编辑用户
    SUBSCRIPTION_VIEW = 0x10   # 查看订阅
    SUBSCRIPTION_EDIT = 0x20   # 编辑订阅
    SYSTEM_CONFIG = 0x40       # 系统配置
    FULL_ACCESS = 0xff         # 完全访问权限
    
    # 默认角色
    @staticmethod
    def insert_roles():
        roles = {
            'user': [0],
            'teacher': [Role.CORRECTION_VIEW, Role.CORRECTION_EDIT],
            'operator': [Role.CORRECTION_VIEW, Role.USER_VIEW, 
                        Role.SUBSCRIPTION_VIEW, Role.SUBSCRIPTION_EDIT],
            'admin': [Role.FULL_ACCESS]
        }
        
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = sum(roles[r])
            role.description = f"{r.capitalize()} role"
            db.session.add(role)
        db.session.commit()
    
    def has_permission(self, permission):
        """检查角色是否有指定权限"""
        return self.permissions & permission == permission
```

### 3.2 权限验证装饰器

```python
def admin_required(permission=0):
    """
    验证管理员权限的装饰器
    
    Args:
        permission: 所需权限代码，默认为0（只需要管理员身份）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 验证用户已登录
            if not hasattr(g, 'user') or not g.user.is_authenticated():
                return jsonify({
                    "status": "error",
                    "message": "请先登录",
                    "code": "login_required"
                }), 401
            
            # 验证用户是否为管理员
            if g.user.role.name not in ['admin', 'operator', 'teacher']:
                return jsonify({
                    "status": "error",
                    "message": "无访问权限",
                    "code": "admin_required"
                }), 403
            
            # 验证具体权限
            if permission > 0 and not g.user.role.has_permission(permission):
                return jsonify({
                    "status": "error",
                    "message": "权限不足",
                    "code": "permission_denied"
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

## 4. API接口设计

### 4.1 用户管理接口

```python
@admin_bp.route('/users', methods=['GET'])
@admin_required(Role.USER_VIEW)
def get_users():
    """获取用户列表"""
    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 搜索过滤
    username = request.args.get('username', '')
    email = request.args.get('email', '')
    role = request.args.get('role', '')
    
    # 构建查询
    query = User.query
    
    if username:
        query = query.filter(User.username.like(f'%{username}%'))
    if email:
        query = query.filter(User.email.like(f'%{email}%'))
    if role:
        query = query.join(Role).filter(Role.name == role)
    
    # 执行查询
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    users = pagination.items
    
    # 格式化响应
    return jsonify({
        'status': 'success',
        'data': {
            'users': [user.to_dict() for user in users],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
    })
```

### 4.2 作文管理接口

```python
@admin_bp.route('/essays', methods=['GET'])
@admin_required(Role.CORRECTION_VIEW)
def get_essays():
    """获取作文列表"""
    # 实现类似用户列表的查询功能...
```

### 4.3 数据统计接口

```python
@admin_bp.route('/stats', methods=['GET'])
@admin_required()
def get_stats():
    """获取系统统计数据"""
    # 获取统计时间范围
    start_date = request.args.get('start_date', 
                  (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # 转换为datetime对象
    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # 获取各项统计数据
    new_users = User.query.filter(
        User.created_at.between(start_datetime, end_datetime)
    ).count()
    
    new_essays = Essay.query.filter(
        Essay.submission_time.between(start_datetime, end_datetime)
    ).count()
    
    new_subscriptions = Subscription.query.filter(
        Subscription.created_at.between(start_datetime, end_datetime)
    ).count()
    
    # 返回统计数据
    return jsonify({
        'status': 'success',
        'data': {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'users': {
                'total': User.query.count(),
                'new': new_users
            },
            'essays': {
                'total': Essay.query.count(),
                'new': new_essays
            },
            'subscriptions': {
                'total': Subscription.query.count(),
                'new': new_subscriptions,
                'active': Subscription.query.filter_by(status='active').count()
            }
        }
    })
```

## 5. 功能模块

### 5.1 用户管理功能

- 用户列表查询与筛选
- 用户详情查看
- 用户角色分配
- 用户账号禁用/启用
- 重置用户密码

### 5.2 作文批改管理

- 作文列表查询与筛选
- 批改结果查看与编辑
- 批改质量评估
- 批改历史记录

### 5.3 会员订阅管理

- 会员套餐设置
- 订阅记录管理
- 支付记录查询
- 手动调整会员权限

### 5.4 数据统计与分析

- 用户增长趋势
- 作文提交统计
- 订阅转化率
- 收入统计

### 5.5 系统配置管理

- 批改参数配置
- 系统公告设置
- 邮件模板管理
- 敏感词过滤设置

## 6. 权限管理实现

### 6.1 权限检查中间件

```python
@admin_bp.before_request
def before_admin_request():
    """管理后台请求前置处理"""
    # 验证用户是否已登录
    if not hasattr(g, 'user') or not g.user.is_authenticated():
        if request.path.startswith('/api/admin'):
            return jsonify({
                "status": "error",
                "message": "请先登录",
                "code": "login_required"
            }), 401
    
    # 验证用户是否有管理权限
    if g.user and g.user.is_authenticated():
        if g.user.role.name not in ['admin', 'operator', 'teacher']:
            if request.path.startswith('/api/admin'):
                return jsonify({
                    "status": "error",
                    "message": "无访问权限",
                    "code": "admin_required"
                }), 403
```

## 7. 前端界面设计

管理界面布局：
- 左侧导航菜单
- 顶部状态栏
- 主内容区
- 信息展示卡片
- 数据表格和图表

## 8. 数据可视化

采用Echarts实现以下数据可视化：
- 用户增长趋势图
- 作文提交数量统计图
- 订阅转化漏斗图
- 收入趋势图

## 9. 安全措施

- 操作日志记录
- 敏感操作二次确认
- API请求频率限制
- 管理员操作权限分级 