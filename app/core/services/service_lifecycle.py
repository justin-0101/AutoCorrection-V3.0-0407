import logging
from typing import Any, Dict, Optional, List, Set, Callable
from enum import Enum
from datetime import datetime
from threading import Lock

logger = logging.getLogger('app.core.services')

class ServiceLifecycleEvent(Enum):
    """服务生命周期事件枚举"""
    CREATED = 'created'           # 服务实例被创建
    INITIALIZING = 'initializing' # 服务开始初始化
    INITIALIZED = 'initialized'    # 服务初始化完成
    STARTING = 'starting'         # 服务开始启动
    STARTED = 'started'           # 服务已启动
    STOPPING = 'stopping'         # 服务开始停止
    STOPPED = 'stopped'           # 服务已停止
    FAILED = 'failed'            # 服务发生错误
    DEGRADED = 'degraded'        # 服务降级运行
    RECOVERING = 'recovering'     # 服务正在恢复
    RECOVERED = 'recovered'       # 服务已恢复
    DESTROYING = 'destroying'     # 服务开始销毁
    DESTROYED = 'destroyed'       # 服务已销毁

class ServiceLifecycleState:
    """服务生命周期状态"""
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.current_event = ServiceLifecycleEvent.CREATED
        self.last_event_time = datetime.utcnow()
        self.error_count = 0
        self.recovery_attempts = 0
        self.last_error: Optional[Exception] = None
        self.is_healthy = True
        self.metrics: Dict[str, float] = {}
        
    def update_event(self, event: ServiceLifecycleEvent, error: Optional[Exception] = None) -> None:
        """更新服务状态"""
        self.current_event = event
        self.last_event_time = datetime.utcnow()
        
        if event == ServiceLifecycleEvent.FAILED:
            self.error_count += 1
            self.last_error = error
            self.is_healthy = False
        elif event == ServiceLifecycleEvent.RECOVERED:
            self.is_healthy = True
            self.recovery_attempts = 0
        elif event == ServiceLifecycleEvent.RECOVERING:
            self.recovery_attempts += 1

class ServiceLifecycleManager:
    """服务生命周期管理器"""
    
    def __init__(self):
        self._states: Dict[str, ServiceLifecycleState] = {}
        self._listeners: Dict[ServiceLifecycleEvent, List[Callable]] = {}
        self._lock = Lock()
        
    def register_service(self, service_name: str) -> None:
        """注册服务到生命周期管理器"""
        with self._lock:
            if service_name not in self._states:
                self._states[service_name] = ServiceLifecycleState(service_name)
                logger.info(f"服务 '{service_name}' 已注册到生命周期管理器")
    
    def update_service_state(self, service_name: str, event: ServiceLifecycleEvent, 
                           error: Optional[Exception] = None) -> None:
        """更新服务状态"""
        with self._lock:
            if service_name not in self._states:
                self.register_service(service_name)
            
            state = self._states[service_name]
            state.update_event(event, error)
            
            # 触发事件监听器
            self._notify_listeners(service_name, event, state)
            
            logger.info(f"服务 '{service_name}' 状态更新为: {event.value}")
    
    def register_listener(self, event: ServiceLifecycleEvent, 
                         callback: Callable[[str, ServiceLifecycleState], None]) -> None:
        """注册事件监听器"""
        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(callback)
    
    def _notify_listeners(self, service_name: str, event: ServiceLifecycleEvent, 
                         state: ServiceLifecycleState) -> None:
        """通知所有相关的事件监听器"""
        listeners = self._listeners.get(event, [])
        for listener in listeners:
            try:
                listener(service_name, state)
            except Exception as e:
                logger.error(f"执行事件监听器时出错: {str(e)}")
    
    def get_service_state(self, service_name: str) -> Optional[ServiceLifecycleState]:
        """获取服务状态"""
        return self._states.get(service_name)
    
    def get_unhealthy_services(self) -> List[str]:
        """获取所有不健康的服务"""
        return [name for name, state in self._states.items() if not state.is_healthy]
    
    def get_all_services_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务的状态信息"""
        status = {}
        for name, state in self._states.items():
            status[name] = {
                'current_event': state.current_event.value,
                'last_event_time': state.last_event_time.isoformat(),
                'error_count': state.error_count,
                'recovery_attempts': state.recovery_attempts,
                'is_healthy': state.is_healthy,
                'metrics': state.metrics
            }
        return status
    
    def try_recover_service(self, service_name: str) -> bool:
        """尝试恢复服务"""
        state = self._states.get(service_name)
        if not state:
            return False
            
        if not state.is_healthy:
            self.update_service_state(service_name, ServiceLifecycleEvent.RECOVERING)
            # 实际恢复逻辑应该由具体的服务实现
            return True
            
        return False
    
    def update_service_metrics(self, service_name: str, metrics: Dict[str, float]) -> None:
        """更新服务的度量指标"""
        state = self._states.get(service_name)
        if state:
            state.metrics.update(metrics)
            
# 创建全局生命周期管理器实例
lifecycle_manager = ServiceLifecycleManager() 