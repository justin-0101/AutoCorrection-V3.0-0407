"""
监控模块
负责系统监控、指标收集和告警功能
"""

from .monitor_service import (
    MetricsStore, AlertManager, metrics_store, alert_manager,
    init_monitoring, start_monitoring_service, stop_monitoring_service
)

def setup_monitoring(app):
    """
    设置Flask应用的监控
    
    Args:
        app: Flask应用实例
    """
    monitoring = init_monitoring()
    app.monitoring = monitoring
    return monitoring

__all__ = [
    'MetricsStore', 'AlertManager', 'metrics_store', 'alert_manager',
    'setup_monitoring', 'start_monitoring_service', 'stop_monitoring_service'
] 