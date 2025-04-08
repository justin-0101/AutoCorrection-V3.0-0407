import logging
from datetime import datetime
from app.core.services.service_container import ServiceContainer

logger = logging.getLogger('app.core.services')

class HealthChecker:
    """服务健康检查器"""
    
    @classmethod
    def check_service_health(cls, service_name):
        """检查指定服务的健康状态"""
        service = ServiceContainer.get(service_name)
        if not service:
            logger.error(f"服务 '{service_name}' 不存在")
            return False
            
        try:
            if hasattr(service, 'health_check'):
                return service.health_check()
            return True
        except Exception as e:
            logger.error(f"服务 '{service_name}' 健康检查失败: {str(e)}")
            return False
    
    @classmethod
    def check_all_services(cls):
        """检查所有已注册服务的健康状态"""
        results = {}
        for service_name in ServiceContainer._services:
            is_healthy = cls.check_service_health(service_name)
            results[service_name] = {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'last_check': datetime.now().isoformat()
            }
        return results
        
    @classmethod
    def get_service_metrics(cls):
        """获取服务性能指标"""
        metrics = {}
        for service_name, service in ServiceContainer._services.items():
            if hasattr(service, 'get_metrics'):
                try:
                    metrics[service_name] = service.get_metrics()
                except Exception as e:
                    logger.error(f"获取服务 '{service_name}' 指标失败: {str(e)}")
        return metrics 