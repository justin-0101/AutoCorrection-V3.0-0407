# 系统部署与配置指南

## 1. 概述

本文档提供作文批改平台的部署与配置指南，包括开发环境、测试环境和生产环境的部署方法，以及系统配置、性能优化建议等。

## 2. 系统要求

### 2.1 硬件要求

- **最低配置**：
  - CPU: 2核
  - 内存: 4GB
  - 存储: 20GB SSD

- **推荐配置**：
  - CPU: 4核或更高
  - 内存: 8GB或更高
  - 存储: 50GB SSD

### 2.2 软件要求

- Python 3.8+
- SQLite 3.30+ (开发) / MySQL 8.0+ (生产)
- Redis 6.0+
- Nginx 1.18+ (生产环境)
- Node.js 14+ (前端开发)

## 3. 开发环境搭建

### 3.1 获取代码

```bash
# 克隆代码仓库
git clone https://github.com/yourusername/autocorrection.git
cd autocorrection
```

### 3.2 创建虚拟环境

```bash
# 创建Python虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3.3 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 3.4 配置环境变量

创建`.env`文件配置环境变量：

```
# .env 文件内容
# 应用配置
DEBUG=True
SECRET_KEY=your-secret-key-for-development
FLASK_APP=app.py

# 数据库配置
DATABASE_URL=sqlite:///autocorrection.db

# Redis配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# 邮件配置
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=your-email@example.com
```

### 3.5 初始化数据库

```bash
# 初始化数据库
flask db upgrade

# 添加初始数据
flask seed
```

### 3.6 启动开发服务器

```bash
# 启动Redis (如未运行)
redis-server

# 启动Celery Worker
celery -A tasks.celery_app:celery_app worker --loglevel=info

# 启动Celery Beat (定时任务)
celery -A tasks.celery_app:celery_app beat --loglevel=info

# 启动Flask开发服务器
flask run

# 启动前端开发服务器
cd frontend
npm run serve
```

## 4. 测试环境部署

### 4.1 使用Docker Compose快速部署

创建`docker-compose.yml`文件：

```yaml
version: '3'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - redis
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=development
      - DEBUG=True
      - SECRET_KEY=your-secret-key-for-testing
      - DATABASE_URL=sqlite:///autocorrection.db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    volumes:
      - .:/app

  worker:
    build: .
    command: celery -A tasks.celery_app:celery_app worker --loglevel=info
    depends_on:
      - redis
    environment:
      - DATABASE_URL=sqlite:///autocorrection.db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    volumes:
      - .:/app

  beat:
    build: .
    command: celery -A tasks.celery_app:celery_app beat --loglevel=info
    depends_on:
      - redis
    environment:
      - DATABASE_URL=sqlite:///autocorrection.db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    volumes:
      - .:/app

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
```

启动测试环境：

```bash
docker-compose up -d
```

## 5. 生产环境部署

### 5.1 前期准备

- 获取域名和SSL证书
- 设置DNS记录
- 准备生产服务器
- 创建数据库

### 5.2 系统配置

修改`.env`文件为生产配置：

```
# 生产环境配置
DEBUG=False
SECRET_KEY=your-strong-production-secret-key
FLASK_APP=app.py
FLASK_ENV=production

# 数据库配置 (使用MySQL)
DATABASE_URL=mysql+pymysql://username:password@localhost/autocorrection

# Redis配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# 邮件配置
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=/var/log/autocorrection

# 备份配置
BACKUP_DIR=/var/backups/autocorrection
```

### 5.3 Nginx配置

创建Nginx配置文件：

```nginx
# /etc/nginx/sites-available/autocorrection.conf
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # 重定向HTTP到HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL配置
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    
    # 静态文件
    location /static {
        alias /path/to/autocorrection/static;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }
    
    # API代理
    location /api {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket代理
    location /socket.io {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 前端应用
    location / {
        root /path/to/autocorrection/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }
    
    # 安全设置
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' data: https://cdn.jsdelivr.net; connect-src 'self' wss://$host;";
}
```

### 5.4 使用Supervisor管理进程

创建Supervisor配置：

```ini
; /etc/supervisor/conf.d/autocorrection.conf
[program:autocorrection_web]
command=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
directory=/path/to/autocorrection
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/autocorrection/web.err.log
stdout_logfile=/var/log/autocorrection/web.out.log

[program:autocorrection_worker]
command=/path/to/venv/bin/celery -A tasks.celery_app:celery_app worker --loglevel=info
directory=/path/to/autocorrection
user=www-data
numprocs=1
autostart=true
autorestart=true
stderr_logfile=/var/log/autocorrection/worker.err.log
stdout_logfile=/var/log/autocorrection/worker.out.log

[program:autocorrection_beat]
command=/path/to/venv/bin/celery -A tasks.celery_app:celery_app beat --loglevel=info
directory=/path/to/autocorrection
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/autocorrection/beat.err.log
stdout_logfile=/var/log/autocorrection/beat.out.log
```

启动Supervisor服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
```

## 6. 部署脚本

### 6.1 一键部署脚本

```bash
#!/bin/bash
# deploy.sh - 一键部署脚本

set -e  # 遇到错误立即退出

# 确认是否继续
read -p "此操作将部署作文批改平台到生产环境，是否继续？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "部署已取消"
    exit 1
fi

# 更新代码
echo "正在更新代码..."
git pull

# 安装/更新依赖
echo "正在更新依赖..."
source venv/bin/activate
pip install -r requirements.txt

# 构建前端
echo "正在构建前端..."
cd frontend
npm install
npm run build
cd ..

# 数据库迁移
echo "正在更新数据库..."
flask db upgrade

# 重启服务
echo "正在重启服务..."
sudo supervisorctl restart autocorrection_web
sudo supervisorctl restart autocorrection_worker
sudo supervisorctl restart autocorrection_beat

# 清理缓存
echo "正在清理缓存..."
rm -rf /tmp/autocorrection_cache/*

echo "部署完成！"
```

## 7. 系统监控与维护

### 7.1 监控系统健康

```bash
# 检查服务状态
sudo supervisorctl status

# 检查日志
tail -f /var/log/autocorrection/web.err.log
tail -f /var/log/autocorrection/worker.err.log

# 检查系统资源
htop
```

### 7.2 数据库维护

```bash
# 备份数据库
mysqldump -u username -p autocorrection > backup_$(date +%Y%m%d).sql

# 优化数据库
mysqlcheck -o autocorrection -u username -p
```

## 8. 性能优化

### 8.1 Web服务器优化

- 启用Gzip压缩
- 配置静态文件缓存
- 使用CDN分发静态资源
- 优化Nginx工作进程数量

### 8.2 应用服务器优化

- 调整Gunicorn工作进程数
- 优化数据库连接池
- 启用应用级缓存
- 配置异步任务并发数

### 8.3 数据库优化

- 添加适当的索引
- 定期清理过期数据
- 优化查询语句
- 配置数据库缓存

## 9. 安全配置

### 9.1 防火墙设置

```bash
# 仅开放必要端口
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 9.2 安全更新

```bash
# 定期更新系统
sudo apt update
sudo apt upgrade -y

# 更新应用依赖
pip install -U -r requirements.txt
```

## 10. 故障恢复

### 10.1 数据恢复

```bash
# 从备份恢复数据库
mysql -u username -p autocorrection < backup_20230101.sql

# 恢复配置文件
cp /etc/autocorrection/config.bak /etc/autocorrection/config.py
```

### 10.2 系统恢复

```bash
# 重置应用状态
flask reset-error-status

# 重启所有服务
sudo supervisorctl restart all
``` 