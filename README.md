# 作文批改系统 (AutoCorrection V2.0)

基于人工智能的作文批改系统，提供智能评分、详细点评和建议改进的在线服务平台。

## 功能特点

- **智能评分**：使用AI模型对作文进行全方位评分
- **详细点评**：提供语言、结构、内容等多维度的专业点评
- **历史记录**：支持查看历史作文和评分记录
- **用户管理**：完整的用户注册、登录和个人中心功能
- **实时反馈**：即时的评分结果和改进建议
- **安全可靠**：采用安全的数据存储和用户认证机制
- **日志追踪**：完整的日志记录系统，支持问题排查和用户行为分析

## 技术栈

- **后端**：Python + Flask
- **前端**：HTML + CSS + JavaScript
- **数据库**：SQLite
- **AI模型**：DashScope API
- **Web服务器**：Nginx + Gunicorn
- **日志系统**：Python logging + Werkzeug

## 系统要求

- Python 3.8+
- Nginx 1.20+
- CentOS Stream 9（推荐）或其他Linux发行版
- 4GB+ RAM
- 20GB+ 存储空间

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/your-username/AutoCorrection-V2.0.git
cd AutoCorrection-V2.0
```

### 2. 安装依赖
```bash
python -m venv .venv
source .venv/bin/activate  # Linux
# 或 .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
# 创建 .env 文件并添加以下内容
DASHSCOPE_API_KEY=your_api_key_here
FLASK_ENV=development  # 开发环境使用 development，生产环境使用 production
FLASK_APP=app.py
```

### 4. 初始化数据库
```bash
python init_db.py
```

### 5. 启动服务
根据您的操作系统，选择相应的启动方式：

#### Windows环境
```bash
python run_all_services.py
```
这将启动所有必要的服务：
- Redis服务器
- Celery工作进程
- Flask Web应用

#### Linux环境
```bash
chmod +x start_server.sh  # 首次运行前添加执行权限
./start_server.sh --all   # 启动所有服务
```

支持的启动参数：
- `--all`: 启动所有服务（Redis、Celery、Web）
- `--debug`: 开启调试模式
- `--port PORT`: 指定Web服务器端口（默认5000）
- `--workers`: 仅启动Celery工作进程
- `--workers-only`: 仅启动Celery（不启动Web服务器）
- `--concurrency N`: 设置Celery工作进程数（默认2）

服务启动后，访问 http://localhost:5000 开始使用系统。

## 开发模式特性

1. **调试模式**
   - 默认启用 Flask 调试器
   - 代码修改后自动重载
   - 详细的错误追踪

2. **日志系统**
   - 控制台实时日志输出
   - 文件日志记录
   - 分级日志（INFO, WARNING, ERROR）
   - 用户操作追踪

3. **性能监控**
   - 请求响应时间记录
   - 数据库查询统计
   - 系统资源使用监控

## 日志系统说明

系统使用多级日志记录机制：

1. **应用日志**
   - 位置：`logs/app.log`
   - 内容：系统运行状态、用户操作记录
   - 格式：`时间 - 级别 - 信息`

2. **访问日志**
   - 位置：`logs/access.log`
   - 内容：HTTP请求记录、响应时间
   - 格式：标准 NGINX 访问日志格式

3. **错误日志**
   - 位置：`logs/error.log`
   - 内容：系统错误、异常堆栈
   - 格式：详细的错误追踪信息

4. **AI评分日志**
   - 位置：`logs/ai_scoring.log`
   - 内容：AI模型调用记录、评分过程
   - 格式：`时间 - 作文ID - 评分结果`

## 部署说明

详细的部署指南请参考 [部署指南](docs/部署指南.md)。

## 目录结构

```
AutoCorrection-V2.0/
├── app.py              # 主应用入口
├── init_db.py         # 数据库初始化脚本
├── requirements.txt   # 项目依赖
├── static/           # 静态资源文件
├── templates/        # HTML模板
├── instance/         # 实例配置和数据
├── uploads/         # 上传文件目录
└── docs/            # 文档目录
```

## 主要功能模块

1. **用户管理**
   - 用户注册和登录
   - 个人信息管理
   - 密码重置

2. **作文批改**
   - 作文提交和评分
   - 详细评语生成
   - 修改建议

3. **历史记录**
   - 作文历史查看
   - 评分记录统计
   - 进步追踪

4. **系统管理**
   - 日志记录
   - 性能监控
   - 数据备份

## 使用说明

1. **注册/登录**
   - 首次使用需要注册账号
   - 使用邮箱和密码登录

2. **提交作文**
   - 在主页点击"提交作文"
   - 输入或上传作文内容
   - 等待AI评分结果

3. **查看结果**
   - 查看详细评分和建议
   - 保存或导出评分报告
   - 查看历史记录

## 常见问题

1. **系统无法启动**
   - 检查环境变量配置
   - 确认数据库是否初始化
   - 查看错误日志

2. **评分服务异常**
   - 验证API密钥是否有效
   - 检查网络连接
   - 查看服务器日志

3. **日志输出重复**
   - 这是因为日志同时配置了控制台和文件输出
   - 在开发模式下属于正常现象
   - 生产环境下会自动优化日志输出

## 维护与支持

- 定期检查日志文件
  ```bash
  # 查看实时日志
  tail -f logs/app.log
  
  # 查看错误日志
  tail -f logs/error.log
  
  # 查看访问日志
  tail -f logs/access.log
  ```
- 备份数据库文件
- 更新系统依赖
- 监控系统性能
- 定期清理日志文件
  ```bash
  # 清理30天前的日志
  find logs/ -name "*.log" -mtime +30 -delete
  ```

## 贡献指南

欢迎提交问题报告和改进建议。如果您想贡献代码：

1. Fork 本仓库
2. 创建您的特性分支
3. 提交您的改动
4. 推送到您的分支
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目Issues
- 电子邮件：179579938@qq.com

## 致谢

感谢所有为本项目做出贡献的开发者和用户。

## 快速提交代码

为了简化git提交流程，项目提供了一个批处理脚本 `git-push.bat`。使用方法：

1. 双击运行 `git-push.bat`
2. 在提示时输入提交信息
3. 等待脚本完成提交和推送

注意事项：
- 每次提交前请确保代码修改是完整的
- 提交信息应该简明扼要地描述本次修改内容
- 如果遇到冲突或其他错误，请手动解决后再使用脚本

## Pandoc说明

本项目使用Pandoc进行文档转换，但由于文件大小限制，`pandoc.exe`不包含在代码库中。

### 安装Pandoc

1. 访问Pandoc官方网站：https://pandoc.org/installing.html
2. 下载并安装适合您系统的版本
3. 将pandoc添加到系统环境变量中

或者直接下载项目所需版本：
[Pandoc 2.19.2 Windows x64](https://github.com/jgm/pandoc/releases/download/2.19.2/pandoc-2.19.2-windows-x86_64.msi)

安装完成后，请将pandoc.exe放置在项目的`pandoc`目录下。

##特别说明
1、本项目截止2025年4月8日，功能仍不完善，提交作文、批改作文和管理后台的运行报错还未解决。
