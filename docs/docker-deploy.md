# Docker 部署指南

## 前置条件

- 确保云服务器已安装 Docker 和 Docker Compose
- 已获取项目代码

## 部署步骤

1. 将项目代码上传到云服务器
```bash
# 使用scp命令上传（Windows用户可以使用WinSCP等工具）
scp -r ./AutoCorrection-V2.0 user@your-server-ip:/path/to/deploy
```

2. 登录到云服务器并进入项目目录
```bash
ssh user@your-server-ip
cd /path/to/deploy/AutoCorrection-V2.0
```

3. 构建并启动服务
```bash
# 构建并启动所有服务
docker-compose up -d --build
```

4. 验证服务状态
```bash
# 查看容器运行状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app
```

## 常用操作

- 停止服务：`docker-compose down`
- 重启服务：`docker-compose restart`
- 查看日志：`docker-compose logs -f`
- 更新部署：
  ```bash
  # 拉取最新代码
  git pull
  
  # 重新构建并启动
  docker-compose up -d --build
  ```

## 注意事项

1. 确保服务器防火墙已开放80端口（Nginx使用）
2. 如需使用HTTPS，请配置SSL证书并修改nginx.conf
3. 建议定期备份static目录下的数据

## 故障排除

1. 如果服务无法启动，检查日志：
```bash
docker-compose logs app
docker-compose logs nginx
```

2. 如果端口被占用：
```bash
# 查看占用端口的进程
sudo lsof -i :80
```

3. 如果需要清理Docker缓存：
```bash
docker system prune -a
```