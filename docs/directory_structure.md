# 项目目录结构说明

## 核心目录

### `app/` - 应用程序核心目录
- 包含应用程序的主要代码
- 包括路由、视图、模型等核心功能

### `core/` - 核心功能模块
- 包含系统核心功能实现
- 基础服务和工具类

### `api/` - API接口模块
- RESTful API接口
- API版本控制
- API文档

### `instance/` - Flask实例配置
- 特定实例的配置
- 实例级别的设置

### `config/` - 配置文件目录
- `.env` - 环境变量配置
- `.env.example` - 环境变量示例
- `redis.conf` - Redis配置
- `.editorconfig` - 编辑器配置
- `ai_scoring_result.json` - AI评分配置

### `scripts/` - 脚本文件目录
- `checks/` - 系统检查脚本
  - 包含各种系统状态检查工具
- `db/` - 数据库相关脚本
  - 数据库初始化和管理工具
- `fixes/` - 修复脚本
  - 系统问题修复工具
- `run/` - 运行脚本
  - 包含主要的运行和服务启动脚本
- `utils/` - 工具脚本
  - 各种实用工具脚本

## 数据目录

### `database/` - 数据库文件目录
- 存储SQLite数据库文件
- 数据库备份

### `uploads/` - 上传文件目录
- 用户上传的文件存储位置

### `logs/` - 日志目录
- 应用程序日志
- 系统日志

## 前端相关

### `frontend/` - 前端代码目录
- `node_modules/` - Node.js依赖
- `package.json` - 前端依赖配置
- `admin_demo.html` - 管理界面演示

### `static/` - 静态文件目录
- CSS、JavaScript、图片等静态资源

### `templates/` - 模板文件目录
- HTML模板文件

### `www/` - Web服务目录
- Web服务器配置
- 静态资源服务

## 文档和部署

### `docs/` - 文档目录
- 项目文档
- API文档
- 部署指南

### `deploy/` - 部署配置目录
- `Dockerfile` - Docker构建文件
- `docker-compose.yml` - Docker编排配置
- `nginx.conf` - Nginx配置
- 其他部署相关脚本

## 测试相关

### `tests/` - 测试代码目录
- 单元测试
- 集成测试
- E2E测试

## 工具目录

### `pandoc/` - 文档转换工具
- Pandoc配置和模板
- 文档格式转换脚本

### `poppler/` - PDF处理工具
- PDF转换和处理工具
- PDF相关配置

## 其他目录

### `migrations/` - 数据库迁移文件
- 数据库架构变更记录

### `rules/` - 规则配置目录
- 业务规则配置文件

### `ssl/` - SSL证书目录
- SSL证书和密钥

### `redis/` - Redis数据目录
- Redis持久化数据

### `.venv/` - Python虚拟环境
- Python依赖包

## 归档目录

### `archive/` - 通用归档目录
- 历史文件存档
- 备份文件

### `modules_archive_20250408_124637/` - 模块归档
- 存档的旧版本模块

### `chc/` 和 `chenhongchun/` - 临时文档目录
- 开发文档和笔记

## 根目录文件

### 配置文件
- `requirements.txt` - Python依赖配置
- `.gitignore` - Git忽略配置
- `README.md` - 项目说明文档

## 目录结构图

```
AutoCorrection-V3.0-0407/
├── app/                    # 应用程序核心代码
├── core/                   # 核心功能模块
├── api/                    # API接口模块
├── instance/               # Flask实例配置
├── config/                 # 配置文件
├── scripts/                # 脚本文件
│   ├── checks/            # 检查脚本
│   ├── db/                # 数据库脚本
│   ├── fixes/             # 修复脚本
│   ├── run/               # 运行脚本
│   └── utils/             # 工具脚本
├── database/              # 数据库文件
├── frontend/              # 前端代码
├── docs/                  # 文档
├── deploy/                # 部署配置
├── tests/                 # 测试代码
├── static/                # 静态文件
├── templates/             # 模板文件
├── www/                   # Web服务
├── pandoc/                # 文档转换工具
├── poppler/               # PDF处理工具
├── uploads/               # 上传文件
├── logs/                  # 日志文件
├── migrations/            # 数据库迁移
├── rules/                 # 规则配置
├── ssl/                   # SSL证书
├── redis/                 # Redis数据
├── archive/               # 通用归档
├── .venv/                 # Python虚拟环境
└── modules_archive_*/     # 模块归档
``` 