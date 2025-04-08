# 系统监控与备份设计

## 1. 概述

系统监控与备份模块负责确保作文批改平台的稳定运行和数据安全，主要包括性能监控、错误监控、日志管理和数据备份恢复等功能。本文档概述了该模块的设计方案。

## 2. 系统监控架构

### 2.1 监控组件

系统监控采用分层架构：
- 数据采集层：收集系统指标、日志和错误信息
- 数据处理层：分析和处理监控数据
- 存储层：存储监控数据和历史记录
- 可视化层：通过仪表盘展示监控数据
- 报警层：根据预设规则触发报警

### 2.2 监控指标

关键监控指标包括：
- CPU使用率
- 内存使用情况
- 磁盘空间和I/O
- 数据库性能
- API响应时间
- 请求成功率
- 批改任务队列长度
- 活跃用户数

## 3. 性能监控实现

### 3.1 服务器性能监控

```python
# utils/monitoring.py
def check_system_health():
    """检查系统健康状态"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'cpu': {
            'usage_percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count()
        },
        'memory': {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'used_percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total': psutil.disk_usage('/').total,
            'free': psutil.disk_usage('/').free,
            'used_percent': psutil.disk_usage('/').percent
        },
        'status': 'normal'
    }
    
    # 设置状态
    if report['cpu']['usage_percent'] > 90 or report['memory']['used_percent'] > 90:
        report['status'] = 'warning'
    
    if report['disk']['used_percent'] > 90:
        report['status'] = 'critical'
    
    return report
```

### 3.2 API性能监控中间件

```python
# middleware/monitoring.py
@app.before_request
def start_timer():
    """记录请求开始时间"""
    g.start_time = time.time()

@app.after_request
def log_request_info(response):
    """记录API响应时间和状态"""
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        
        # 记录慢请求
        if duration > 0.5:  # 500ms以上视为慢请求
            endpoint = request.endpoint or 'unknown'
            logger.warning(f"慢请求: {request.method} {request.path} "
                           f"({endpoint}) - {duration:.2f}秒")
        
        # 统计API性能指标
        metric_key = f"api.{request.endpoint}.response_time"
        metrics.timing(metric_key, duration * 1000)  # 转换为毫秒
        
        # 记录状态码
        metrics.increment(f"api.status.{response.status_code}")
    
    return response
```

## 4. 错误监控与报警系统

### 4.1 异常处理

```python
# utils/error_handler.py
def handle_exception(exc):
    """处理和记录异常"""
    error_id = str(uuid.uuid4())
    user_id = getattr(g, 'user', None) and g.user.id
    
    error_data = {
        'error_id': error_id,
        'timestamp': datetime.now().isoformat(),
        'type': exc.__class__.__name__,
        'message': str(exc),
        'traceback': traceback.format_exc(),
        'user_id': user_id,
        'endpoint': request.endpoint,
        'url': request.url,
        'method': request.method,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent.string
    }
    
    # 记录错误日志
    logger.error(f"异常 [{error_id}]: {exc.__class__.__name__}: {str(exc)}", 
                 extra=error_data)
    
    # 严重错误发送报警
    if isinstance(exc, (DatabaseError, OperationalError)) or is_critical_error(exc):
        send_error_alert(error_data)
    
    return error_data
```

### 4.2 报警系统

```python
# utils/alert.py
def send_error_alert(error_data):
    """发送错误报警"""
    alert = {
        'title': f"错误报警: {error_data['type']}",
        'message': f"发生严重错误: {error_data['message']}",
        'error_id': error_data['error_id'],
        'level': get_error_level(error_data),
        'timestamp': error_data['timestamp']
    }
    
    # 根据错误级别选择不同的通知方式
    if alert['level'] == 'critical':
        # 高危错误：短信+邮件+微信通知
        send_sms_alert(alert)
        send_email_alert(alert)
        send_wechat_alert(alert)
    elif alert['level'] == 'warning':
        # 警告：邮件+微信通知
        send_email_alert(alert)
        send_wechat_alert(alert)
    else:
        # 普通错误：仅记录到监控系统
        log_alert(alert)
```

## 5. 日志管理

### 5.1 日志配置

```python
# config/logging_config.py
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'json': {
            'format': '%(message)s',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': os.path.join(LOG_DIR, 'app.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'json',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True
        },
        'app': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'api': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

### 5.2 日志分析工具

```python
# utils/log_analyzer.py
def analyze_error_logs(period='1d'):
    """分析错误日志"""
    # 实现详细代码...
```

## 6. 数据备份策略

### 6.1 数据备份配置

数据备份采用多层次策略：
- 定时全量备份：每天凌晨进行一次完整备份
- 增量备份：每小时进行一次增量备份
- 事务日志备份：每10分钟进行一次事务日志备份
- 跨地域备份：备份数据同步到不同地区的备份存储

### 6.2 备份实现

```python
# tasks/backup_tasks.py
@shared_task(name='tasks.backup_tasks.daily_backup')
def daily_backup():
    """每日全量备份"""
    backup_date = datetime.now().strftime('%Y%m%d')
    backup_path = os.path.join(settings.BACKUP_DIR, f'full_{backup_date}.sql')
    
    logger.info(f"开始每日全量备份，路径: {backup_path}")
    
    try:
        # 创建备份目录
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # 执行数据库备份命令
        cmd = [
            'sqlite3',
            settings.DATABASE_PATH,
            f'.backup "{backup_path}"'
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # 压缩备份文件
        with open(backup_path, 'rb') as f_in:
            with gzip.open(f'{backup_path}.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 删除未压缩的文件
        os.remove(backup_path)
        
        # 更新备份记录
        record_backup_history('full', f'{backup_path}.gz')
        
        logger.info(f"每日全量备份完成: {backup_path}.gz")
        
        # 上传到远程存储
        upload_to_remote_storage(f'{backup_path}.gz')
        
        return {
            'status': 'success',
            'backup_file': f'{backup_path}.gz',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"备份失败: {str(e)}", exc_info=True)
        send_backup_failure_alert(str(e))
        
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }
```

## 7. 灾难恢复方案

### 7.1 恢复流程

系统实现了自动恢复流程：
1. 故障检测：监控系统检测到严重故障
2. 故障评估：确定故障类型和影响范围
3. 恢复决策：根据故障类型选择恢复策略
4. 执行恢复：自动或手动执行恢复操作
5. 验证恢复：验证系统功能是否正常
6. 故障分析：分析故障原因并记录

### 7.2 恢复实现

```python
# utils/recovery.py
def restore_from_backup(backup_file=None, target_time=None):
    """从备份恢复数据库"""
    # 如果未指定备份文件，查找最近的有效备份
    if not backup_file and not target_time:
        backup_file = find_latest_backup()
    elif target_time:
        # 基于时间点查找最近的备份
        backup_file = find_backup_by_time(target_time)
    
    if not backup_file:
        raise ValueError("未找到有效的备份文件")
    
    logger.info(f"开始从备份恢复: {backup_file}")
    
    try:
        # 停止应用服务
        stop_application_services()
        
        # 解压备份文件
        temp_db_file = decompress_backup(backup_file)
        
        # 备份当前数据库
        backup_current_db()
        
        # 恢复数据库
        restore_database(temp_db_file)
        
        # 应用事务日志（如果是时间点恢复）
        if target_time:
            apply_transaction_logs(target_time)
        
        # 启动应用服务
        start_application_services()
        
        # 验证恢复结果
        if verify_database_integrity():
            logger.info(f"数据库恢复成功: {backup_file}")
            send_recovery_success_notification(backup_file)
            return True
        else:
            logger.error(f"数据库恢复后完整性校验失败")
            rollback_recovery()
            return False
            
    except Exception as e:
        logger.error(f"恢复失败: {str(e)}", exc_info=True)
        rollback_recovery()
        send_recovery_failure_alert(str(e))
        return False
```

## 8. 监控仪表盘

系统提供Web监控仪表盘，展示：
- 实时系统状态
- 性能指标趋势图
- 错误统计和分布
- API调用统计
- 资源使用情况
- 任务队列状态
- 备份状态和历史

## 9. 安全考虑

监控和备份系统的安全措施：
- 监控数据加密存储
- 备份文件加密
- 访问控制和权限管理
- 安全审计日志
- 敏感信息脱敏 