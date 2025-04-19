#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
健康检查服务
提供系统服务健康状态检查
"""

import logging
import time
from typing import Dict, Any, List
import traceback
import os

from app.core.services.container import container

logger = logging.getLogger(__name__)

class HealthChecker:
    """健康检查服务"""
    
    def __init__(self):
        """初始化健康检查服务"""
        logger.info("初始化健康检查服务")
    
    def check_all_services(self) -> Dict[str, Any]:
        """
        检查所有服务的健康状态
        
        Returns:
            Dict: 检查结果
        """
        start_time = time.time()
        results = {}
        
        # 检查容器服务
        try:
            container_services = list(container.get_all().keys())
            results['container'] = {
                'status': 'ok',
                'services': container_services,
                'count': len(container_services)
            }
        except Exception as e:
            results['container'] = {
                'status': 'error',
                'message': str(e)
            }
        
        # 检查Redis服务
        try:
            redis_service = container.get('redis_service')
            if redis_service:
                ping_result = redis_service.ping()
                results['redis'] = {
                    'status': 'ok' if ping_result else 'error',
                    'message': 'PONG' if ping_result else 'Failed to ping Redis'
                }
            else:
                results['redis'] = {
                    'status': 'not_available',
                    'message': 'Redis service not registered'
                }
        except Exception as e:
            results['redis'] = {
                'status': 'error',
                'message': str(e)
            }
        
        # 检查文件服务
        try:
            file_service = container.get('file_service')
            if file_service:
                results['file_service'] = {
                    'status': 'ok',
                    'message': 'File service available'
                }
            else:
                results['file_service'] = {
                    'status': 'not_available',
                    'message': 'File service not registered'
                }
        except Exception as e:
            results['file_service'] = {
                'status': 'error',
                'message': str(e)
            }
        
        # 检查AI服务
        try:
            ai_factory = container.get('ai_client_factory')
            if ai_factory:
                results['ai_service'] = {
                    'status': 'ok',
                    'message': 'AI client factory available'
                }
            else:
                results['ai_service'] = {
                    'status': 'not_available',
                    'message': 'AI client factory not registered'
                }
        except Exception as e:
            results['ai_service'] = {
                'status': 'error',
                'message': str(e)
            }
        
        # 检查Celery
        try:
            from app.tasks.celery_app import celery_app
            i = celery_app.control.inspect()
            stats = i.stats()
            if stats:
                results['celery'] = {
                    'status': 'ok',
                    'workers': len(stats),
                    'stats': stats
                }
            else:
                results['celery'] = {
                    'status': 'warning',
                    'message': 'No active Celery workers found'
                }
        except Exception as e:
            results['celery'] = {
                'status': 'error',
                'message': str(e)
            }
        
        # 添加环境信息
        results['environment'] = {
            'debug': os.environ.get('DEBUG', 'False'),
            'flask_env': os.environ.get('FLASK_ENV', 'production'),
            'deepseek_api_key_set': bool(os.environ.get('DEEPSEEK_API_KEY', ''))
        }
        
        # 计算总体状态
        has_error = any(s.get('status') == 'error' for s in results.values())
        has_warning = any(s.get('status') == 'warning' for s in results.values())
        
        overall_status = 'error' if has_error else ('warning' if has_warning else 'ok')
        
        # 返回结果
        return {
            'status': overall_status,
            'services': results,
            'duration_ms': int((time.time() - start_time) * 1000)
        }
    
    def check_file_service(self) -> Dict[str, Any]:
        """
        检查文件服务
        
        Returns:
            Dict: 检查结果
        """
        try:
            file_service = container.get('file_service')
            if not file_service:
                return {
                    'status': 'not_available',
                    'message': 'File service not registered'
                }
            
            # 检查必要文件夹是否存在
            folders = ['uploads', 'temp']
            folder_status = {}
            
            for folder in folders:
                path = os.path.join('app', folder)
                exists = os.path.exists(path)
                writable = os.access(path, os.W_OK) if exists else False
                
                folder_status[folder] = {
                    'path': path,
                    'exists': exists,
                    'writable': writable
                }
            
            return {
                'status': 'ok',
                'folders': folder_status
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }
    
    def check_correction_service(self) -> Dict[str, Any]:
        """检查批改服务"""
        try:
            # 从依赖注入容器获取批改服务
            from app.core.services.service_registry_di import ServiceContainer
            # 导入 CorrectionService (如果需要类型检查)
            # from app.core.correction.correction_service import CorrectionService
            
            correction_service_provider = getattr(ServiceContainer, 'correction_service', None)
            if correction_service_provider:
                # 检查批改服务状态
                # 注意：这里我们只检查provider是否存在，不实例化服务以避免副作用
                return {
                    'status': 'ok',
                    'message': 'Correction service provider available'
                }
            
            # 尝试直接从容器获取 (假设 container 已正确导入或可用)
            # 需要确保 container 在此作用域可用
            # from app.core.services.container import container # 可能需要导入
            correction_service = container.get('correction_service')
            if correction_service:
                return {
                    'status': 'ok',
                    'message': 'Correction service available in container'
                }
            
            return {
                'status': 'not_available',
                'message': 'Correction service not found'
            }
        except Exception as e:
            # 导入 traceback (如果尚未在文件顶部导入)
            import traceback 
            return {
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }