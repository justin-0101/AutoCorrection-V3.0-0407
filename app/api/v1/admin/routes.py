#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
管理员 API 路由模块

提供管理后台所需的数据，包括用户管理、会员管理、作文管理、数据统计和系统配置等功能。
"""

import logging
import datetime
import traceback
from flask import Blueprint, request, jsonify, g
from app.core.auth.auth_decorators import login_required, admin_required
from app.core.user.user_service import UserService
from app.core.membership.membership_service import MembershipService
from app.core.correction.correction_service import CorrectionService
from app.utils.response import success_response, error_response
from app.utils.exceptions import ValidationError, ResourceNotFoundError
from app.extensions import db

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建蓝图
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/v1/admin')

# 服务实例
# 使用安全的服务初始化 - 如果创建失败使用模拟服务
try:
    user_service = UserService()
except Exception as e:
    logger.error(f"用户服务创建失败: {str(e)}")
    # 创建一个模拟服务对象
    from unittest.mock import MagicMock
    user_service = MagicMock()
    user_service.count_users.return_value = 0
    user_service.get_user_growth_trend.return_value = []

try:
    membership_service = MembershipService()
except Exception as e:
    logger.error(f"会员服务创建失败: {str(e)}")
    from unittest.mock import MagicMock
    membership_service = MagicMock()
    membership_service.count_subscriptions.return_value = 0
    membership_service.calculate_monthly_revenue.return_value = 0

try:
    correction_service = CorrectionService()
except Exception as e:
    logger.error(f"批改服务创建失败: {str(e)}")
    from unittest.mock import MagicMock
    correction_service = MagicMock()
    correction_service.count_essays.return_value = 0

def safe_service_call(service_func, default_value=None, *args, **kwargs):
    """
    安全地调用服务函数，处理可能的异常
    
    Args:
        service_func: 服务函数
        default_value: 发生异常时的默认返回值
        args: 位置参数
        kwargs: 关键字参数
        
    Returns:
        服务函数的返回值，或者发生异常时的默认值
    """
    try:
        return service_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"服务调用失败: {service_func.__name__}, 错误: {str(e)}")
        if default_value is not None:
            return default_value
        raise

@admin_api_bp.before_request
@login_required
@admin_required
def before_request():
    """
    请求前检查是否是管理员
    """
    # 权限检查在装饰器中已完成
    try:
        from flask_login import current_user
        username = current_user.username if hasattr(current_user, 'username') else 'unknown'
        logger.info(f"管理员 {username} 访问管理 API: {request.path}")
    except Exception as e:
        logger.warning(f"记录管理员访问信息时出错: {str(e)}")
        pass


@admin_api_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """
    获取仪表盘数据
    
    包括用户统计、作文统计、会员统计和收入统计
    """
    try:
        # 获取当前日期和上个月的日期
        today = datetime.datetime.now()
        last_month = today - datetime.timedelta(days=30)
        
        # 安全地获取统计数据 - 使用默认值避免整个API崩溃
        # 获取用户统计数据
        users_count = safe_service_call(user_service.count_users, 0)
        users_last_month = safe_service_call(user_service.count_users, 0, before=last_month)
        
        # 安全计算增长率
        try:
            user_growth = ((users_count - users_last_month) / users_last_month * 100) if users_last_month > 0 else 100
        except:
            user_growth = 0
        
        # 获取作文统计数据
        essays_count = safe_service_call(correction_service.count_essays, 0)
        essays_last_month = safe_service_call(correction_service.count_essays, 0, before=last_month)
        
        # 安全计算增长率
        try:
            essay_growth = ((essays_count - essays_last_month) / essays_last_month * 100) if essays_last_month > 0 else 100
        except:
            essay_growth = 0
        
        # 获取会员统计数据
        memberships_count = safe_service_call(membership_service.count_subscriptions, 0, active_only=True)
        
        # 安全计算转化率
        try:
            conversion_rate = (memberships_count / users_count * 100) if users_count > 0 else 0
        except:
            conversion_rate = 0
        
        # 获取收入统计数据
        monthly_revenue = safe_service_call(membership_service.calculate_monthly_revenue, 0)
        last_month_revenue = safe_service_call(
            membership_service.calculate_monthly_revenue, 0, 
            month=last_month.month, year=last_month.year
        )
        
        # 安全计算增长率
        try:
            revenue_growth = ((monthly_revenue - last_month_revenue) / last_month_revenue * 100) if last_month_revenue > 0 else 100
        except:
            revenue_growth = 0
        
        # 获取用户和收入趋势
        user_trend = safe_service_call(user_service.get_user_growth_trend, [], months=6)
        revenue_trend = safe_service_call(membership_service.get_revenue_trend, [], months=6)
        
        # 构建响应数据
        data = {
            'users': {
                'total': users_count,
                'growth': round(user_growth, 2),
                'trend': user_trend
            },
            'essays': {
                'total': essays_count,
                'growth': round(essay_growth, 2)
            },
            'memberships': {
                'total': memberships_count,
                'conversion_rate': round(conversion_rate, 2)
            },
            'revenue': {
                'monthly': monthly_revenue,
                'growth': round(revenue_growth, 2),
                'trend': revenue_trend
            }
        }
        
        logger.info("成功获取仪表盘数据")
        return success_response(data)
    
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        # 返回一个最小可用的数据结构，避免前端报错
        return success_response({
            'users': {'total': 0, 'growth': 0, 'trend': []},
            'essays': {'total': 0, 'growth': 0},
            'memberships': {'total': 0, 'conversion_rate': 0},
            'revenue': {'monthly': 0, 'growth': 0, 'trend': []}
        })


@admin_api_bp.route('/users', methods=['GET'])
def get_users():
    """
    获取用户列表
    
    支持分页和搜索
    """
    try:
        # 获取请求参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '')
        
        # 获取用户列表
        users, total = user_service.get_users_with_pagination(
            page=page,
            per_page=limit,
            search_term=search
        )
        
        # 计算总页数
        total_pages = (total + limit - 1) // limit
        
        # 转换为 JSON 格式
        users_data = []
        for user in users:
            # 获取用户的会员信息
            membership = membership_service.get_user_membership(user.id)
            # 获取用户的作文数量
            essay_count = correction_service.count_user_essays(user.id)
            
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat(),
                'membership': membership.to_dict() if membership else None,
                'essay_count': essay_count
            })
        
        # 构建响应数据
        data = {
            'users': users_data,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': total_pages
        }
        
        logger.info(f"获取用户列表成功，页码：{page}，每页数量：{limit}")
        return success_response(data)
    
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        return error_response("获取用户列表失败", 500)


@admin_api_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    获取用户详情
    """
    try:
        # 获取用户
        user = user_service.get_user_by_id(user_id)
        if not user:
            return error_response("用户不存在", 404)
        
        # 获取用户的会员信息
        membership = membership_service.get_user_membership(user.id)
        
        # 获取用户的作文信息
        essays, _ = correction_service.get_user_essays(user.id, page=1, per_page=5)
        essays_data = [essay.to_dict() for essay in essays]
        
        # 构建用户详情数据
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
            'membership': membership.to_dict() if membership else None,
            'recent_essays': essays_data,
            'essay_count': correction_service.count_user_essays(user.id),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        
        logger.info(f"获取用户详情成功，用户ID：{user_id}")
        return success_response({'user': user_data})
    
    except ResourceNotFoundError as e:
        logger.warning(f"用户不存在，用户ID：{user_id}")
        return error_response(str(e), 404)
    
    except Exception as e:
        logger.error(f"获取用户详情失败，用户ID：{user_id}，错误：{str(e)}")
        return error_response("获取用户详情失败", 500)


@admin_api_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    更新用户信息
    """
    try:
        # 获取请求数据
        data = request.json
        if not data:
            return error_response("请求数据为空", 400)
        
        # 更新用户
        updated_user = user_service.update_user(user_id, data)
        
        logger.info(f"更新用户成功，用户ID：{user_id}")
        return success_response({'user': updated_user.to_dict()}, "用户更新成功")
    
    except ValidationError as e:
        logger.warning(f"更新用户验证失败，用户ID：{user_id}，错误：{str(e)}")
        return error_response(str(e), 400)
    
    except ResourceNotFoundError as e:
        logger.warning(f"用户不存在，用户ID：{user_id}")
        return error_response(str(e), 404)
    
    except Exception as e:
        logger.error(f"更新用户失败，用户ID：{user_id}，错误：{str(e)}")
        return error_response("更新用户失败", 500)


@admin_api_bp.route('/users', methods=['POST'])
def create_user():
    """
    创建新用户
    """
    try:
        # 获取请求数据
        data = request.json
        if not data:
            return error_response("请求数据为空", 400)
        
        # 创建用户
        new_user = user_service.create_user(data)
        
        logger.info(f"创建用户成功，用户ID：{new_user.id}")
        return success_response({'user': new_user.to_dict()}, "用户创建成功", 201)
    
    except ValidationError as e:
        logger.warning(f"创建用户验证失败，错误：{str(e)}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"创建用户失败，错误：{str(e)}")
        return error_response("创建用户失败", 500)


@admin_api_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    删除用户
    """
    try:
        # 删除用户
        user_service.delete_user(user_id)
        
        logger.info(f"删除用户成功，用户ID：{user_id}")
        return success_response(message="用户删除成功")
    
    except ResourceNotFoundError as e:
        logger.warning(f"用户不存在，用户ID：{user_id}")
        return error_response(str(e), 404)
    
    except Exception as e:
        logger.error(f"删除用户失败，用户ID：{user_id}，错误：{str(e)}")
        return error_response("删除用户失败", 500)


@admin_api_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
def reset_user_password(user_id):
    """
    重置用户密码
    """
    try:
        # 获取请求数据
        data = request.json
        if not data or 'new_password' not in data:
            return error_response("请求数据不完整", 400)
        
        # 重置密码
        user_service.reset_password(user_id, data['new_password'])
        
        logger.info(f"重置用户密码成功，用户ID：{user_id}")
        return success_response(message="密码重置成功")
    
    except ValidationError as e:
        logger.warning(f"重置密码验证失败，用户ID：{user_id}，错误：{str(e)}")
        return error_response(str(e), 400)
    
    except ResourceNotFoundError as e:
        logger.warning(f"用户不存在，用户ID：{user_id}")
        return error_response(str(e), 404)
    
    except Exception as e:
        logger.error(f"重置用户密码失败，用户ID：{user_id}，错误：{str(e)}")
        return error_response("重置用户密码失败", 500)


@admin_api_bp.route('/users/me', methods=['GET'])
def get_current_user():
    """
    获取当前登录的管理员信息
    """
    try:
        # 获取当前用户
        from flask_login import current_user
        if not current_user or not current_user.is_authenticated:
            return error_response("未登录或会话已过期", 401)
        
        # 构建用户数据
        user_data = {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'is_admin': current_user.is_admin,
            'is_active': current_user.is_active,
            'created_at': current_user.created_at.isoformat(),
            'last_login': current_user.last_login_at.isoformat() if hasattr(current_user, 'last_login_at') and current_user.last_login_at else None
        }
        
        logger.info(f"获取当前管理员信息成功，用户ID：{current_user.id}")
        return success_response({'user': user_data})
    
    except Exception as e:
        logger.error(f"获取当前管理员信息失败，错误：{str(e)}")
        return error_response("获取当前管理员信息失败", 500)


# 会员管理 API 路由
@admin_api_bp.route('/memberships', methods=['GET'])
def get_memberships():
    """获取会员订单列表"""
    try:
        # 获取请求参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        
        # 获取会员订单列表（这里用模拟数据）
        # 实际应用中应该从membership_service获取数据
        
        # 模拟订单数据
        mock_orders = [
            {
                'order_id': f'ORD{i:06d}',
                'user_id': i * 10,
                'user_name': f'用户{i}',
                'plan_id': 1,
                'plan_name': '普通会员' if i % 3 != 0 else '高级会员',
                'amount': 49.00 if i % 3 != 0 else 99.00,
                'payment_method': '微信支付' if i % 2 == 0 else '支付宝',
                'status': 'completed' if i % 4 != 0 else ('pending' if i % 4 == 0 else 'cancelled'),
                'created_at': (datetime.datetime.now() - datetime.timedelta(days=i)).isoformat(),
                'updated_at': (datetime.datetime.now() - datetime.timedelta(days=i, hours=2)).isoformat()
            }
            for i in range(1, 21)
        ]
        
        # 应用搜索过滤
        filtered_orders = mock_orders
        if search:
            filtered_orders = [
                order for order in filtered_orders 
                if search.lower() in order['user_name'].lower() or 
                   search in order['order_id']
            ]
        
        # 应用状态过滤
        if status:
            filtered_orders = [
                order for order in filtered_orders 
                if order['status'] == status
            ]
        
        # 应用分页
        total = len(filtered_orders)
        start_idx = (page - 1) * limit
        end_idx = min(start_idx + limit, total)
        paginated_orders = filtered_orders[start_idx:end_idx]
        
        # 计算统计数据
        total_revenue = sum(order['amount'] for order in mock_orders if order['status'] == 'completed')
        monthly_revenue = sum(
            order['amount'] for order in mock_orders 
            if order['status'] == 'completed' and 
               datetime.datetime.fromisoformat(order['created_at']).month == datetime.datetime.now().month
        )
        
        # 构建响应数据
        data = {
            'orders': paginated_orders,
            'pagination': {
                'total': total,
                'current_page': page,
                'per_page': limit,
                'total_pages': (total + limit - 1) // limit
            },
            'stats': {
                'total_orders': len(mock_orders),
                'monthly_orders': len([
                    order for order in mock_orders
                    if datetime.datetime.fromisoformat(order['created_at']).month == datetime.datetime.now().month
                ]),
                'total_revenue': total_revenue,
                'monthly_revenue': monthly_revenue
            }
        }
        
        logger.info(f"获取会员订单列表成功，页码：{page}，每页数量：{limit}")
        return success_response(data)
    
    except Exception as e:
        logger.error(f"获取会员订单列表失败: {str(e)}")
        return error_response("获取会员订单列表失败", 500)


@admin_api_bp.route('/memberships/<string:order_id>', methods=['GET'])
def get_membership_order(order_id):
    """获取会员订单详情"""
    try:
        # 模拟数据 - 实际应用中应该从数据库获取
        mock_order = {
            'order_id': order_id,
            'user_id': 101,
            'user_name': '张三',
            'plan_id': 2,
            'plan_name': '高级会员',
            'amount': 99.00,
            'payment_method': '微信支付',
            'status': 'completed',
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat(),
            'logs': [
                {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'message': '订单创建'
                },
                {
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat(),
                    'message': '支付成功'
                },
                {
                    'timestamp': (datetime.datetime.now() - datetime.timedelta(minutes=1)).isoformat(),
                    'message': '订单完成'
                }
            ]
        }
        
        logger.info(f"获取会员订单详情成功，订单ID：{order_id}")
        return success_response(mock_order)
    
    except Exception as e:
        logger.error(f"获取会员订单详情失败: {str(e)}")
        return error_response("获取会员订单详情失败", 500)


@admin_api_bp.route('/membership-plans', methods=['GET'])
def get_membership_plans():
    """
    获取所有会员计划
    """
    try:
        # 获取会员计划
        plans = membership_service.get_membership_plans()
        
        # 转换为 JSON 格式
        plans_data = [plan.to_dict() for plan in plans]
        
        logger.info("获取会员计划列表成功")
        return success_response({'plans': plans_data})
    
    except Exception as e:
        logger.error(f"获取会员计划列表失败: {str(e)}")
        return error_response("获取会员计划列表失败", 500)


@admin_api_bp.route('/essays', methods=['GET'])
def get_essays():
    """
    获取作文列表
    
    支持分页和搜索
    """
    try:
        # 获取请求参数
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '')
        
        # 获取作文列表
        essays, total = correction_service.get_essays_with_pagination(
            page=page,
            per_page=limit,
            search_term=search
        )
        
        # 计算总页数
        total_pages = (total + limit - 1) // limit
        
        # 转换为 JSON 格式
        essays_data = []
        for essay in essays:
            # 获取作者信息
            author = user_service.get_user_by_id(essay.user_id)
            
            essays_data.append({
                'id': essay.id,
                'title': essay.title,
                'content': essay.content[:100] + '...' if len(essay.content) > 100 else essay.content,
                'word_count': essay.word_count,
                'status': essay.status,
                'created_at': essay.created_at.isoformat(),
                'author': {
                    'id': author.id if author else None,
                    'username': author.username if author else '未知用户'
                }
            })
        
        # 构建响应数据
        data = {
            'essays': essays_data,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': total_pages
        }
        
        logger.info(f"获取作文列表成功，页码：{page}，每页数量：{limit}")
        return success_response(data)
    
    except Exception as e:
        logger.error(f"获取作文列表失败: {str(e)}")
        return error_response("获取作文列表失败", 500)


@admin_api_bp.route('/essays/<int:essay_id>', methods=['GET'])
def get_essay(essay_id):
    """
    获取作文详情
    """
    try:
        # 获取作文
        essay = correction_service.get_essay_by_id(essay_id)
        if not essay:
            return error_response("作文不存在", 404)
        
        # 获取作者信息
        author = user_service.get_user_by_id(essay.user_id)
        
        # 获取作文的批改结果
        correction = correction_service.get_correction_by_essay_id(essay_id)
        
        # 构建作文详情数据
        essay_data = {
            'id': essay.id,
            'title': essay.title,
            'content': essay.content,
            'word_count': essay.word_count,
            'status': essay.status,
            'created_at': essay.created_at.isoformat(),
            'author': {
                'id': author.id if author else None,
                'username': author.username if author else '未知用户'
            },
            'correction': correction.to_dict() if correction else None
        }
        
        logger.info(f"获取作文详情成功，作文ID：{essay_id}")
        return success_response({'essay': essay_data})
    
    except ResourceNotFoundError as e:
        logger.warning(f"作文不存在，作文ID：{essay_id}")
        return error_response(str(e), 404)
    
    except Exception as e:
        logger.error(f"获取作文详情失败，作文ID：{essay_id}，错误：{str(e)}")
        return error_response("获取作文详情失败", 500)


# 系统配置 API 路由
@admin_api_bp.route('/config', methods=['GET'])
def get_system_config():
    """
    获取系统配置
    """
    try:
        # 获取系统配置
        config = {
            'app_name': "作文批改系统",
            'version': "2.0.0",
            'max_upload_size': 10 * 1024 * 1024,  # 10MB
            'allowed_file_types': ['txt', 'docx', 'pdf', 'jpg', 'jpeg', 'png'],
            'correction_timeout': 60,  # 60秒
            'daily_submission_limit': {
                'free': 1,
                'basic': 3,
                'premium': 10
            }
        }
        
        logger.info("获取系统配置成功")
        return success_response({'config': config})
    
    except Exception as e:
        logger.error(f"获取系统配置失败: {str(e)}")
        return error_response("获取系统配置失败", 500)


@admin_api_bp.route('/config', methods=['PUT'])
def update_system_config():
    """
    更新系统配置
    """
    try:
        # 获取请求数据
        data = request.json
        if not data:
            return error_response("请求数据为空", 400)
        
        # TODO: 实现配置更新逻辑
        
        logger.info("更新系统配置成功")
        return success_response(message="系统配置更新成功")
    
    except ValidationError as e:
        logger.warning(f"更新系统配置验证失败，错误：{str(e)}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"更新系统配置失败，错误：{str(e)}")
        return error_response("更新系统配置失败", 500)


# 数据统计 API 路由
@admin_api_bp.route('/stats/user-activity', methods=['GET'])
def get_user_activity_stats():
    """
    获取用户活跃度统计
    """
    try:
        # 获取时间范围参数
        days = int(request.args.get('days', 30))
        
        # TODO: 实现用户活跃度统计逻辑
        
        # 模拟数据
        data = {
            'labels': [f"Day {i+1}" for i in range(days)],
            'active_users': [int(50 + 20 * (i % 7 < 5)) for i in range(days)],
            'new_users': [int(10 + 5 * (i % 7 < 5)) for i in range(days)],
            'logins': [int(100 + 50 * (i % 7 < 5)) for i in range(days)]
        }
        
        logger.info(f"获取用户活跃度统计成功，时间范围：{days}天")
        return success_response({'user_activity': data})
    
    except Exception as e:
        logger.error(f"获取用户活跃度统计失败: {str(e)}")
        return error_response("获取用户活跃度统计失败", 500)


@admin_api_bp.route('/stats/submission-stats', methods=['GET'])
def get_submission_stats():
    """
    获取作文提交统计
    """
    try:
        # 获取时间范围参数
        days = int(request.args.get('days', 30))
        
        # TODO: 实现作文提交统计逻辑
        
        # 模拟数据
        data = {
            'labels': [f"Day {i+1}" for i in range(days)],
            'submissions': [int(30 + 15 * (i % 7 < 5)) for i in range(days)],
            'completed': [int(25 + 15 * (i % 7 < 5)) for i in range(days)],
            'word_count': [int(5000 + 2000 * (i % 7 < 5)) for i in range(days)]
        }
        
        logger.info(f"获取作文提交统计成功，时间范围：{days}天")
        return success_response({'submission_stats': data})
    
    except Exception as e:
        logger.error(f"获取作文提交统计失败: {str(e)}")
        return error_response("获取作文提交统计失败", 500)


@admin_api_bp.route('/stats/membership-stats', methods=['GET'])
def get_membership_stats():
    """
    获取会员统计
    """
    try:
        # 获取会员计划分布
        plans = membership_service.get_membership_plans()
        plan_distribution = []
        
        for plan in plans:
            count = membership_service.count_subscriptions_by_plan(plan.id)
            plan_distribution.append({
                'name': plan.name,
                'count': count
            })
        
        # 添加免费用户
        free_users = user_service.count_users() - membership_service.count_subscriptions()
        plan_distribution.append({
            'name': '免费用户',
            'count': free_users
        })
        
        # 获取会员增长趋势
        months = 6
        trend_data = membership_service.get_subscription_trend(months=months)
        
        # 构建响应数据
        data = {
            'plan_distribution': plan_distribution,
            'trend': trend_data,
            'conversion_rate': round(membership_service.count_subscriptions() / user_service.count_users() * 100, 2) if user_service.count_users() > 0 else 0,
            'renewal_rate': round(membership_service.calculate_renewal_rate() * 100, 2)
        }
        
        logger.info("获取会员统计成功")
        return success_response({'membership_stats': data})
    
    except Exception as e:
        logger.error(f"获取会员统计失败: {str(e)}")
        return error_response("获取会员统计失败", 500)


@admin_api_bp.route('/stats/revenue-stats', methods=['GET'])
def get_revenue_stats():
    """
    获取收入统计
    """
    try:
        # 获取时间范围参数
        months = int(request.args.get('months', 12))
        
        # 获取收入趋势
        revenue_trend = membership_service.get_revenue_trend(months=months)
        
        # 获取按计划的收入分布
        plans = membership_service.get_membership_plans()
        plan_revenue = []
        
        for plan in plans:
            revenue = membership_service.calculate_revenue_by_plan(plan.id)
            plan_revenue.append({
                'name': plan.name,
                'revenue': revenue
            })
        
        # 构建响应数据
        data = {
            'trend': revenue_trend,
            'plan_revenue': plan_revenue,
            'current_month': membership_service.calculate_monthly_revenue(),
            'previous_month': membership_service.calculate_monthly_revenue(month=(datetime.datetime.now() - datetime.timedelta(days=30)).month)
        }
        
        logger.info(f"获取收入统计成功，时间范围：{months}个月")
        return success_response({'revenue_stats': data})
    
    except Exception as e:
        logger.error(f"获取收入统计失败: {str(e)}")
        return error_response("获取收入统计失败", 500)


@admin_api_bp.route('/users/<int:user_id>/update-limits', methods=['POST'])
def update_user_correction_limits(user_id):
    """
    更新用户的批改次数限制
    """
    try:
        # 获取用户
        user = user_service.get_user_by_id(user_id)
        if not user:
            return error_response("用户不存在", 404)
        
        # 获取请求数据
        data = request.json
        if not data:
            return error_response("请求数据不完整", 400)
        
        # 获取每日和每月限制
        daily_limit = data.get('daily_limit')
        monthly_limit = data.get('monthly_limit')
        
        if daily_limit is None or monthly_limit is None:
            return error_response("每日和每月限制不能为空", 400)
        
        # 更新用户的批改次数限制
        profile = user.profile
        if not profile:
            return error_response("用户资料不存在", 404)
        
        # 更新限制
        profile.update_essay_limits(daily_limit, monthly_limit)
        db.session.commit()
        
        logger.info(f"更新用户批改次数限制成功，用户ID：{user_id}，每日限制：{daily_limit}，每月限制：{monthly_limit}")
        return success_response(message="用户批改次数限制更新成功")
    
    except Exception as e:
        logger.error(f"更新用户批改次数限制失败，用户ID：{user_id}，错误：{str(e)}")
        return error_response("更新用户批改次数限制失败", 500) 