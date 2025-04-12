#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
服务监控API
提供服务健康状态和指标监控端点
"""

import logging
from flask import Blueprint, jsonify, Response, current_app
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge
import time

# 创建blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/v1/monitoring')

# 创建prometheus指标收集器
REQUEST_COUNT = Counter(
    'request_count', 'App Request Count',
    ['app_name', 'method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'request_latency_seconds', 'Request latency',
    ['app_name', 'endpoint']
)
CORRECTION_COUNT = Counter(
    'correction_count', 'Correction Count',
    ['status', 'grade']
)
ACTIVE_TASKS = Gauge(
    'active_tasks', 'Active Tasks',
    ['task_type']
)

# 设置任务初始值
ACTIVE_TASKS.labels(task_type='correction').set(0)

# 创建日志记录器
logger = logging.getLogger(__name__)

@monitoring_bp.before_app_request
def start_timer():
    """在请求开始时记录时间"""
    from flask import request, g
    g.start = time.time()

@monitoring_bp.after_app_request
def record_request_metrics(response):
    """记录请求指标"""
    from flask import request, g
    
    if hasattr(g, 'start'):
        resp_time = time.time() - g.start
        REQUEST_LATENCY.labels(
            'essay_correction', 
            request.endpoint
        ).observe(resp_time)
    
    REQUEST_COUNT.labels(
        'essay_correction', 
        request.method, 
        request.endpoint, 
        response.status_code
    ).inc()
    return response

@monitoring_bp.route('/metrics')
def metrics():
    """Prometheus指标端点"""
    from prometheus_client.core import CollectorRegistry
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    try:
        # 从服务容器更新度量指标
        try:
            from app.core.services.service_registry_di import ServiceContainer
            service_metrics = [
                f'service_up{{name="{service}"}} 1' 
                if ServiceContainer.has(service) else
                f'service_up{{name="{service}"}} 0'
                for service in ServiceContainer.get_services()
            ]
        except Exception as e:
            logger.warning(f"无法获取服务状态: {str(e)}")
            service_metrics = []
            
        # 从任务队列更新度量指标
        try:
            from app.tasks.correction_tasks_di import process_essay_correction
            from celery.task.control import inspect
            i = inspect()
            active = i.active() or {}
            
            # 计算活跃的任务数量
            correction_tasks = 0
            for worker, tasks in active.items():
                for task in tasks:
                    if task.get('name') == 'app.tasks.correction_tasks_di.process_essay_correction':
                        correction_tasks += 1
            
            # 更新指标
            ACTIVE_TASKS.labels(task_type='correction').set(correction_tasks)
        except Exception as e:
            logger.warning(f"无法获取任务状态: {str(e)}")
            
        # 生成并返回所有指标
        return Response(
            generate_latest(),
            mimetype=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"生成指标时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@monitoring_bp.route('/health')
def health():
    """健康检查端点"""
    try:
        # 检查数据库连接
        from app.extensions import db
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # 检查Redis
        try:
            from app.core.services.container import container
            redis_service = container.get("redis_service")
            redis_ok = redis_service and redis_service.ping()
        except:
            redis_ok = False
            
        # 检查AI服务
        try:
            from app.core.services.container import container
            ai_client = container.get("ai_client_factory")
            ai_ok = ai_client is not None
        except:
            ai_ok = False
            
        # 返回健康状态
        status = "healthy" if redis_ok and ai_ok else "degraded"
        return jsonify({
            "status": status,
            "version": current_app.config.get('VERSION', 'unknown'),
            "services": {
                "database": "up",
                "redis": "up" if redis_ok else "down",
                "ai_service": "up" if ai_ok else "down"
            }
        })
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@monitoring_bp.route('/services')
def services():
    """服务状态详情端点"""
    try:
        from app.core.services.service_registry_di import ServiceContainer
        
        # 获取所有服务信息
        services_list = ServiceContainer.get_services()
        dependencies = ServiceContainer.get_dependencies()
        
        result = {}
        for service_name in services_list:
            service_deps = dependencies.get(service_name, [])
            service_status = ServiceContainer.has(service_name)
            
            result[service_name] = {
                "status": "up" if service_status else "down",
                "dependencies": service_deps
            }
            
        return jsonify({
            "services": result,
            "count": {
                "total": len(services_list),
                "up": sum(1 for s in result.values() if s["status"] == "up"),
                "down": sum(1 for s in result.values() if s["status"] == "down")
            }
        })
    except Exception as e:
        logger.error(f"获取服务状态时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

def init_app(app):
    """初始化监控模块"""
    app.register_blueprint(monitoring_bp)
    logger.info("监控模块已初始化") 