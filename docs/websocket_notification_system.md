# WebSocket实时通知系统设计

## 1. 概述

WebSocket实时通知系统是作文批改平台的实时交互模块，负责向用户推送作文批改状态、系统通知、会员状态变更等实时信息。本文档详细描述了实时通知系统的设计和实现方案。

## 2. 系统架构

WebSocket通知系统采用以下架构：
- **WebSocket服务**：处理客户端连接和消息推送
- **消息代理(Redis)**：存储和分发消息
- **会话管理**：管理客户端会话和身份验证
- **事件处理器**：处理不同类型的通知事件

### 2.1 架构图

```
┌─────────────────┐     ┌─────────────────┐
│ Flask Web应用   │────►│ Redis消息代理    │
└─────────────────┘     └────────┬────────┘
         ▲                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │ WebSocket服务   │
         │              └────────┬────────┘
         │                       │
         └───────────────────────┘
                       ▲
                       │
                ┌──────┴──────┐
                │  客户端浏览器 │
                └─────────────┘
```

## 3. WebSocket服务实现

### 3.1 初始化WebSocket服务

```python
# websocket/socket_server.py
"""
WebSocket服务
处理实时消息通知
"""
from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
import jwt
from datetime import datetime
import json
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 创建SocketIO实例
socketio = SocketIO(cors_allowed_origins="*")

def init_socketio(app):
    """初始化SocketIO服务"""
    socketio.init_app(
        app,
        message_queue=app.config.get('SOCKETIO_MESSAGE_QUEUE'),
        async_mode='eventlet',  # 使用eventlet作为异步模式
        ping_timeout=30,
        ping_interval=15,
        cors_allowed_origins=app.config.get('CORS_ORIGINS', '*')
    )
    
    # 注册事件处理器
    register_handlers()
    
    logger.info("WebSocket服务已初始化")
    
    return socketio
```

### 3.2 认证中间件

```python
# websocket/auth.py
def authenticate_socket(token):
    """验证Socket连接的token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        
        # 检查token是否过期
        exp = payload.get('exp')
        if not exp or datetime.utcnow().timestamp() > exp:
            return None
            
        # 获取用户信息
        user_id = payload.get('user_id')
        if not user_id:
            return None
            
        return {'user_id': user_id}
    
    except jwt.InvalidTokenError:
        return None
```

### 3.3 连接管理

```python
# websocket/socket_server.py
@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    # 获取认证token
    token = request.args.get('token')
    
    if not token:
        logger.warning(f"WebSocket连接尝试，但未提供认证token，IP: {request.remote_addr}")
        return False
    
    # 验证token
    user_data = authenticate_socket(token)
    if not user_data:
        logger.warning(f"WebSocket连接失败，无效token，IP: {request.remote_addr}")
        return False
    
    # 保存用户信息到会话
    session['user_id'] = user_data['user_id']
    
    # 将用户加入个人房间，用于定向消息
    user_room = f"user_{user_data['user_id']}"
    join_room(user_room)
    
    logger.info(f"用户 {user_data['user_id']} 已连接到WebSocket")
    
    # 发送欢迎消息
    emit('notification', {
        'type': 'welcome',
        'message': '已成功连接到通知服务',
        'timestamp': datetime.now().isoformat()
    })
    
    return True
```

### 3.4 断开连接处理

```python
@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    user_id = session.get('user_id')
    
    if user_id:
        user_room = f"user_{user_id}"
        leave_room(user_room)
        logger.info(f"用户 {user_id} 已断开WebSocket连接")
```

## 4. 事件和消息类型

系统支持以下消息类型：
- `essay_status_update`：作文状态更新通知
- `subscription_status`：会员订阅状态变更
- `system_notice`：系统通知
- `payment_status`：支付状态通知
- `error_alert`：错误提示
- `resource_update`：资源更新通知

### 4.1 消息格式

所有消息遵循统一格式：

```json
{
  "type": "消息类型",
  "timestamp": "ISO格式的时间戳",
  "message": "消息内容",
  "data": {
    // 消息相关的具体数据
  }
}
```

## 5. 消息发送

### 5.1 发送消息到指定用户

```python
# websocket/notification.py
def send_user_notification(user_id, notification_type, message, data=None):
    """向指定用户发送通知"""
    notification = {
        'type': notification_type,
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'data': data or {}
    }
    
    user_room = f"user_{user_id}"
    
    try:
        socketio.emit('notification', notification, room=user_room)
        logger.debug(f"已向用户 {user_id} 发送 {notification_type} 通知")
        return True
    except Exception as e:
        logger.error(f"发送通知给用户 {user_id} 失败: {str(e)}")
        return False
```

### 5.2 发送广播消息

```python
def send_broadcast_notification(notification_type, message, data=None):
    """发送广播通知给所有连接的用户"""
    notification = {
        'type': notification_type,
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'data': data or {}
    }
    
    try:
        socketio.emit('notification', notification, broadcast=True)
        logger.info(f"已广播 {notification_type} 通知")
        return True
    except Exception as e:
        logger.error(f"广播通知失败: {str(e)}")
        return False
```

## 6. 与业务系统集成

### 6.1 作文批改状态通知

```python
# utils/websocket_manager.py
def send_essay_status_update(essay_id, status, user_id=None, error=None):
    """发送作文状态更新通知"""
    # 获取作文信息
    if not user_id:
        essay = Essay.query.get(essay_id)
        if essay:
            user_id = essay.user_id
    
    if not user_id:
        logger.warning(f"无法发送作文状态更新，找不到用户ID，作文ID: {essay_id}")
        return False
    
    # 状态消息映射
    status_messages = {
        'pending': '作文已提交，等待处理',
        'processing': '作文正在批改中',
        'completed': '作文批改已完成',
        'failed': '作文批改失败'
    }
    
    message = status_messages.get(status, f'作文状态: {status}')
    
    # 准备通知数据
    data = {
        'essay_id': essay_id,
        'status': status
    }
    
    if error:
        data['error'] = error
    
    # 发送通知
    return send_user_notification(user_id, 'essay_status_update', message, data)
```

### 6.2 会员订阅状态通知

```python
# utils/websocket_manager.py
def send_subscription_update(user_id, subscription_status, details=None):
    """发送会员订阅状态更新通知"""
    if subscription_status == 'active':
        message = '您的会员订阅已激活'
    elif subscription_status == 'expired':
        message = '您的会员订阅已过期'
    elif subscription_status == 'renewal':
        message = '您的会员订阅已续费'
    else:
        message = f'会员状态已更新: {subscription_status}'
    
    data = {
        'status': subscription_status
    }
    
    if details:
        data.update(details)
    
    return send_user_notification(user_id, 'subscription_status', message, data)
```

## 7. 客户端实现

### 7.1 前端连接代码

```javascript
// 前端WebSocket连接实现
class NotificationService {
  constructor() {
    this.socket = null;
    this.isConnected = false;
    this.eventHandlers = {};
  }
  
  // 连接到WebSocket服务
  connect(token) {
    // 确保只有一个连接
    if (this.socket && this.isConnected) {
      console.log('已经连接到通知服务');
      return;
    }
    
    const socketUrl = `${WEBSOCKET_BASE_URL}?token=${token}`;
    
    this.socket = io(socketUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });
    
    // 设置事件处理器
    this.socket.on('connect', () => {
      console.log('已连接到通知服务');
      this.isConnected = true;
      this._triggerEvent('connect');
    });
    
    this.socket.on('disconnect', () => {
      console.log('与通知服务断开连接');
      this.isConnected = false;
      this._triggerEvent('disconnect');
    });
    
    this.socket.on('notification', (notification) => {
      console.log('收到通知:', notification);
      this._handleNotification(notification);
    });
    
    this.socket.on('connect_error', (error) => {
      console.error('连接错误:', error);
      this._triggerEvent('error', error);
    });
    
    return this;
  }
  
  // 注册事件处理器
  on(event, callback) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    this.eventHandlers[event].push(callback);
    return this;
  }
  
  // 注销事件处理器
  off(event, callback) {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event] = this.eventHandlers[event].filter(
        handler => handler !== callback
      );
    }
    return this;
  }
  
  // 处理收到的通知
  _handleNotification(notification) {
    // 触发通用通知事件
    this._triggerEvent('notification', notification);
    
    // 触发特定类型的通知事件
    if (notification.type) {
      this._triggerEvent(notification.type, notification);
    }
  }
  
  // 触发事件
  _triggerEvent(event, data) {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`事件 ${event} 处理器错误:`, error);
        }
      });
    }
  }
  
  // 断开连接
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
    }
  }
}

// 使用示例
const notificationService = new NotificationService();

// 连接到通知服务
notificationService.connect('用户认证Token');

// 监听作文状态更新
notificationService.on('essay_status_update', (notification) => {
  const { essay_id, status } = notification.data;
  
  if (status === 'completed') {
    // 显示作文批改完成通知
    showToast('批改完成', notification.message);
    // 刷新作文列表或更新UI
    refreshEssayList();
  } else if (status === 'failed') {
    // 显示错误提示
    showErrorMessage(notification.message);
  }
});
```

## 8. 性能优化与扩展性

### 8.1 性能优化

- 使用Redis适配器实现多进程/多服务器支持
- 消息队列缓冲，避免消息峰值时服务过载
- 客户端消息节流与合并，减少连接压力
- 消息压缩，减少网络带宽使用

### 8.2 水平扩展支持

```python
# app.py
# 配置Redis适配器，支持多服务器部署
socketio = SocketIO(
    message_queue='redis://localhost:6379/0',
    channel='socketio',
    async_mode='eventlet'
)
```

## 9. 错误处理与恢复

```python
# websocket/socket_server.py
@socketio.on_error()
def error_handler(e):
    """全局WebSocket错误处理器"""
    user_id = session.get('user_id', 'Unknown')
    logger.error(f"WebSocket错误，用户: {user_id}, 错误: {str(e)}", exc_info=True)
    
    # 向客户端发送错误通知
    emit('notification', {
        'type': 'error',
        'message': '发生服务器错误，可能需要重新连接',
        'timestamp': datetime.now().isoformat()
    })
```

## 10. 安全考虑

WebSocket服务的安全措施包括：
- 基于JWT的连接认证
- 消息加密
- 速率限制，防止DoS攻击
- 连接超时处理
- 输入验证，防止注入攻击
- CORS策略，限制允许的源站 