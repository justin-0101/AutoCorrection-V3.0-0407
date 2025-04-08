# Git 自动化部署指南

## 前置条件

- 确保云服务器已安装 Git
- 已获取项目代码
- 已配置好服务器的 SSH 密钥

## 部署步骤

### 1. 在服务器上初始化Git仓库

```bash
# 登录服务器
ssh user@your-server-ip

# 创建并初始化Git仓库
mkdir -p /path/to/repo && cd /path/to/repo
git init --bare
```

### 2. 配置Git钩子

在服务器上创建post-receive钩子：

```bash
# 进入hooks目录
cd /path/to/repo/hooks

# 创建post-receive文件
cat > post-receive << 'EOF'
#!/bin/bash

# 设置工作目录
DEPLOY_PATH=/path/to/deploy/AutoCorrection-V2.0

# 检出最新代码
git --work-tree=$DEPLOY_PATH --git-dir=/path/to/repo checkout -f main

# 进入部署目录
cd $DEPLOY_PATH

# 使用docker-compose重新构建和启动服务
docker-compose down
docker-compose up -d --build
EOF

# 添加执行权限
chmod +x post-receive
```

### 3. 配置本地Git仓库

```bash
# 添加远程仓库
git remote add production ssh://user@your-server-ip/path/to/repo

# 推送代码
git push production main
```

## 日常部署流程

1. 提交本地更改：
```bash
git add .
git commit -m "your commit message"
```

2. 推送到服务器进行自动部署：
```bash
git push production main
```

## 注意事项

1. 确保服务器上的Git钩子路径配置正确
2. 检查服务器上的Docker和Docker Compose是否正常运行
3. 确保服务器上有足够的磁盘空间
4. 建议在首次部署前备份服务器上的数据

## 故障排除

1. 如果推送失败，检查：
   - SSH连接是否正常
   - Git远程仓库地址是否正确
   - 服务器防火墙设置

2. 如果自动部署失败，检查：
   - Git钩子权限是否正确
   - Docker服务是否正常运行
   - 查看Docker日志：`docker-compose logs`

3. 如需手动触发部署：
   - 登录服务器
   - 进入部署目录
   - 执行：`docker-compose up -d --build`