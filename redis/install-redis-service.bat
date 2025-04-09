@echo off
chcp 65001
echo [信息] 正在安装Redis服务...
sc delete Redis
%~dp0redis-server.exe --service-install %~dp0redis.windows-service.conf --service-name Redis
echo [信息] 正在启动Redis服务...
net start Redis
echo [信息] 完成！
pause 