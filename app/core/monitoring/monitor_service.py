#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
监控服务模块
负责收集、记录和报告系统运行状态，实现告警和通知功能
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import os
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import statistics
from collections import defaultdict, deque

# 创建日志记录器
logger = logging.getLogger(__name__)

# 监控指标存储
class MetricsStore:
    """指标存储类，用于在内存中临时保存监控指标"""
    
    def __init__(self, max_history=1000):
        """
        初始化指标存储
        
        Args:
            max_history: 每个指标保存的最大历史记录数
        """
        self.counters = defaultdict(int)  # 计数器，如任务总数、成功数、失败数
        self.gauges = {}  # 瞬时值，如当前运行任务数
        self.histograms = defaultdict(lambda: deque(maxlen=max_history))  # 分布统计，如任务处理时间
        self.history = defaultdict(lambda: deque(maxlen=max_history))  # 历史记录，如状态变更
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """
        增加计数器值
        
        Args:
            name: 指标名称
            value: 增加的值
            tags: 标签，用于区分不同的指标维度
        """
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        self.counters[key] += value
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        设置瞬时值
        
        Args:
            name: 指标名称
            value: 指标值
            tags: 标签
        """
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        self.gauges[key] = value
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """
        记录直方图数据
        
        Args:
            name: 指标名称
            value: 指标值
            tags: 标签
        """
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        self.histograms[key].append(value)
    
    def record_event(self, name: str, data: Dict[str, Any], tags: Dict[str, str] = None) -> None:
        """
        记录事件数据
        
        Args:
            name: 事件名称
            data: 事件数据
            tags: 标签
        """
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        # 添加时间戳
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.history[key].append(event_data)
    
    def get_counter(self, name: str, tags: Dict[str, str] = None) -> int:
        """获取计数器值"""
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """获取瞬时值"""
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        return self.gauges.get(key)
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """获取直方图统计数据"""
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        
        values = list(self.histograms.get(key, []))
        if not values:
            return {"count": 0}
        
        result = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values)
        }
        
        # 计算百分位数
        if len(values) >= 10:
            values.sort()
            result["p50"] = values[len(values) // 2]
            result["p90"] = values[int(len(values) * 0.9)]
            result["p95"] = values[int(len(values) * 0.95)]
            result["p99"] = values[int(len(values) * 0.99)]
        
        return result
    
    def get_recent_events(self, name: str, limit: int = 10, tags: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """获取最近的事件记录"""
        if tags:
            key = f"{name}:{self._format_tags(tags)}"
        else:
            key = name
        
        events = list(self.history.get(key, []))
        return events[-limit:] if events else []
    
    def _format_tags(self, tags: Dict[str, str]) -> str:
        """将标签格式化为字符串"""
        return ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标数据"""
        return {
            "counters": dict(self.counters),
            "gauges": self.gauges,
            "histograms": {k: self.get_histogram_stats(k) for k in self.histograms},
            "events": {k: len(v) for k, v in self.history.items()}
        }


# 告警管理器
class AlertManager:
    """告警管理器，负责检测异常情况并发送通知"""
    
    def __init__(self):
        """初始化告警管理器"""
        self.alert_rules = []  # 告警规则列表
        self.alert_history = deque(maxlen=1000)  # 告警历史
        self.alert_cooldown = {}  # 告警冷却期，避免重复告警
        self.notification_channels = []  # 通知渠道列表
    
    def create_percentage_rule(self, numerator_metric: str, denominator_metric: str, 
                             threshold: float, operator: str = ">") -> callable:
        """
        创建百分比规则检查函数
        
        Args:
            numerator_metric: 分子指标名称
            denominator_metric: 分母指标名称
            threshold: 阈值
            operator: 比较运算符 (>, <, >=, <=, ==)
        
        Returns:
            callable: 检查函数
        """
        def check_percentage():
            numerator = metrics_store.get_counter(numerator_metric)
            denominator = metrics_store.get_counter(denominator_metric)
            
            if denominator == 0:
                return False, "分母为0，无法计算百分比"
            
            percentage = (numerator / denominator) * 100
            
            if operator == ">" and percentage > threshold:
                return True, f"{numerator_metric}/{denominator_metric}的比率 {percentage:.2f}% 超过了 {threshold}%"
            elif operator == "<" and percentage < threshold:
                return True, f"{numerator_metric}/{denominator_metric}的比率 {percentage:.2f}% 低于 {threshold}%"
            elif operator == ">=" and percentage >= threshold:
                return True, f"{numerator_metric}/{denominator_metric}的比率 {percentage:.2f}% 大于等于 {threshold}%"
            elif operator == "<=" and percentage <= threshold:
                return True, f"{numerator_metric}/{denominator_metric}的比率 {percentage:.2f}% 小于等于 {threshold}%"
            elif operator == "==" and percentage == threshold:
                return True, f"{numerator_metric}/{denominator_metric}的比率 {percentage:.2f}% 等于 {threshold}%"
            
            return False, ""
        
        return check_percentage
    
    def create_threshold_rule(self, metric: str, threshold: float, operator: str = ">",
                            metric_type: str = "counter") -> callable:
        """
        创建阈值规则检查函数
        
        Args:
            metric: 指标名称
            threshold: 阈值
            operator: 比较运算符 (>, <, >=, <=, ==)
            metric_type: 指标类型 (counter, gauge)
        
        Returns:
            callable: 检查函数
        """
        def check_threshold():
            if metric_type == "counter":
                value = metrics_store.get_counter(metric)
            else:  # gauge
                value = metrics_store.get_gauge(metric)
                if value is None:
                    return False, f"指标 {metric} 不存在"
            
            if operator == ">" and value > threshold:
                return True, f"{metric} 的值 {value} 超过了 {threshold}"
            elif operator == "<" and value < threshold:
                return True, f"{metric} 的值 {value} 低于 {threshold}"
            elif operator == ">=" and value >= threshold:
                return True, f"{metric} 的值 {value} 大于等于 {threshold}"
            elif operator == "<=" and value <= threshold:
                return True, f"{metric} 的值 {value} 小于等于 {threshold}"
            elif operator == "==" and value == threshold:
                return True, f"{metric} 的值 {value} 等于 {threshold}"
            
            return False, ""
        
        return check_threshold
    
    def add_notification_channel(self, channel: callable) -> None:
        """
        添加通知渠道
        
        Args:
            channel: 通知函数，接收alert_data参数
        """
        self.notification_channels.append(channel)
    
    def add_alert_rule(self, name: str, check_func, cooldown_minutes: int = 30,
                      severity: str = "warning", description: str = "") -> None:
        """
        添加告警规则
        
        Args:
            name: 规则名称
            check_func: 检查函数，返回(bool, str)，表示是否告警及原因
            cooldown_minutes: 冷却时间（分钟）
            severity: 严重程度 (info, warning, error, critical)
            description: 规则描述
        """
        self.alert_rules.append({
            "name": name,
            "check_func": check_func,
            "cooldown_minutes": cooldown_minutes,
            "severity": severity,
            "description": description
        })
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        检查所有告警规则
        
        Returns:
            触发的告警列表
        """
        triggered_alerts = []
        now = datetime.now()
        
        for rule in self.alert_rules:
            name = rule["name"]
            # 检查冷却期
            if name in self.alert_cooldown:
                if now < self.alert_cooldown[name]:
                    continue
            
            try:
                should_alert, message = rule["check_func"]()
                if should_alert:
                    alert = {
                        "name": name,
                        "severity": rule["severity"],
                        "message": message,
                        "timestamp": now.isoformat()
                    }
                    triggered_alerts.append(alert)
                    self.alert_history.append(alert)
                    
                    # 设置冷却期
                    cooldown_time = now + timedelta(minutes=rule["cooldown_minutes"])
                    self.alert_cooldown[name] = cooldown_time
                    
                    # 发送通知
                    for channel in self.notification_channels:
                        try:
                            channel(alert)
                        except Exception as e:
                            logger.error(f"发送告警通知失败: {str(e)}")
            except Exception as e:
                logger.error(f"检查告警规则 {name} 时出错: {str(e)}")
        
        return triggered_alerts
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的告警记录"""
        alerts = list(self.alert_history)
        return alerts[-limit:] if alerts else []


# 通知渠道实现
class NotificationChannels:
    """通知渠道实现类，提供各种通知方式"""
    
    @staticmethod
    def email_notification(smtp_server: str, port: int, username: str, password: str, 
                          from_addr: str, to_addrs: List[str]) -> callable:
        """
        创建邮件通知函数
        
        Args:
            smtp_server: SMTP服务器地址
            port: 端口
            username: 用户名
            password: 密码
            from_addr: 发件人
            to_addrs: 收件人列表
        
        Returns:
            callable: 通知函数
        """
        def send_notification(alert_data):
            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = ", ".join(to_addrs)
            msg['Subject'] = f"[{alert_data['severity'].upper()}] 系统告警: {alert_data['name']}"
            
            body = f"""
            告警时间: {alert_data['timestamp']}
            严重程度: {alert_data['severity']}
            告警名称: {alert_data['name']}
            告警描述: {alert_data['message']}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(smtp_server, port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
        
        return send_notification
    
    @staticmethod
    def console_notification() -> callable:
        """
        创建控制台通知函数
        
        Returns:
            callable: 通知函数
        """
        def send_notification(alert_data):
            logger.warning(f"系统告警: [{alert_data['severity']}] {alert_data['name']} - {alert_data['message']}")
        
        return send_notification
    
    @staticmethod
    def log_file_notification(file_path: str) -> callable:
        """
        创建日志文件通知函数
        
        Args:
            file_path: 日志文件路径
        
        Returns:
            callable: 通知函数
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        def send_notification(alert_data):
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} [{alert_data['severity']}] "
                       f"{alert_data['name']} - {alert_data['message']}\n")
        
        return send_notification


# 定时任务执行器
class ScheduledExecutor:
    """定时任务执行器，用于定期执行指定的任务"""
    
    def __init__(self):
        """初始化定时任务执行器"""
        self.tasks = {}  # 任务字典，格式为 {name: (interval, func, args, kwargs, last_run)}
        self.running = False
        self.thread = None
    
    def add_task(self, name: str, interval: int, func, *args, **kwargs) -> None:
        """
        添加任务
        
        Args:
            name: 任务名称
            interval: 间隔时间（秒）
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        self.tasks[name] = (interval, func, args, kwargs, None)
    
    def remove_task(self, name: str) -> bool:
        """
        移除任务
        
        Args:
            name: 任务名称
        
        Returns:
            bool: 是否成功移除
        """
        if name in self.tasks:
            del self.tasks[name]
            return True
        return False
    
    def start(self) -> None:
        """启动定时任务执行器"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self) -> None:
        """停止定时任务执行器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
    
    def _run(self) -> None:
        """运行线程"""
        while self.running:
            current_time = time.time()
            
            for name, (interval, func, args, kwargs, last_run) in list(self.tasks.items()):
                if last_run is None or current_time - last_run >= interval:
                    try:
                        func(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"执行任务 {name} 失败: {str(e)}")
                    
                    self.tasks[name] = (interval, func, args, kwargs, current_time)
            
            time.sleep(1)  # 休眠1秒


# 性能计时器装饰器
def timing_decorator(metrics_store, metric_name: str):
    """
    函数执行时间监控装饰器
    
    Args:
        metrics_store: 指标存储实例
        metric_name: 指标名称前缀
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                status = "success"
            except Exception as e:
                status = "error"
                raise
            finally:
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # 转换为毫秒
                
                # 记录执行时间
                metrics_store.record_histogram(
                    f"{metric_name}.duration", 
                    duration,
                    {"status": status}
                )
                
                # 增加调用计数
                metrics_store.increment_counter(
                    f"{metric_name}.calls",
                    1,
                    {"status": status}
                )
            
            return result
        return wrapper
    return decorator


# 全局监控服务实例
metrics_store = MetricsStore()
alert_manager = AlertManager()
scheduled_executor = ScheduledExecutor()

# 初始化控制台通知渠道
alert_manager.add_notification_channel(NotificationChannels.console_notification())

# 默认添加一些监控任务
scheduled_executor.add_task("check_alerts", 60, alert_manager.check_alerts)

# 启动监控服务
def start_monitoring_service():
    """启动监控服务"""
    scheduled_executor.start()
    logger.info("监控服务已启动")

# 停止监控服务
def stop_monitoring_service():
    """停止监控服务"""
    scheduled_executor.stop()
    logger.info("监控服务已停止")

# 添加默认告警规则
def add_default_alert_rules():
    """添加默认告警规则"""
    # 失败率超过20%告警
    alert_manager.add_alert_rule(
        "high_failure_rate",
        alert_manager.create_percentage_rule(
            "essay_correction.failed", "essay_correction.total", 20, ">"
        ),
        cooldown_minutes=30,
        severity="warning",
        description="作文批改失败率过高"
    )
    
    # 处理中任务数过多告警
    alert_manager.add_alert_rule(
        "too_many_processing_tasks",
        alert_manager.create_threshold_rule(
            "essay_correction.processing", 50, ">", metric_type="gauge"
        ),
        cooldown_minutes=15,
        severity="warning",
        description="处理中的作文批改任务过多"
    )
    
    # 平均处理时间过长告警
    def check_long_processing_time(metrics_store):
        stats = metrics_store.get_histogram_stats("essay_correction.duration")
        if stats.get("count", 0) == 0:
            return False, "没有足够的样本"
        
        avg_time = stats.get("avg", 0)
        if avg_time > 300000:  # 5分钟
            return True, f"平均处理时间 {avg_time:.2f}ms 超过了5分钟"
        return False, ""
    
    # 创建一个闭包函数来绑定metrics_store参数
    def check_long_processing_time_wrapper():
        return check_long_processing_time(metrics_store)
    
    alert_manager.add_alert_rule(
        "long_processing_time",
        check_long_processing_time_wrapper,
        cooldown_minutes=30,
        severity="warning",
        description="作文批改平均处理时间过长"
    )
    
    logger.info("已添加默认告警规则")


# 初始化函数
def init_monitoring():
    """初始化监控系统"""
    add_default_alert_rules()
    start_monitoring_service()
    return {
        "metrics_store": metrics_store,
        "alert_manager": alert_manager,
        "scheduled_executor": scheduled_executor
    } 