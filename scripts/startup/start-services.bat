@echo off
title AutoCorrection 服务启动脚本
echo 正在启动所有必要服务...

REM 激活虚拟环境
echo 正在激活虚拟环境...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 激活虚拟环境失败，请确保虚拟环境存在且路径正确
    pause
    exit /b 1
)
echo 虚拟环境已激活

REM 检查 Redis 服务是否已在运行
sc query "Redis" | findstr "RUNNING" > nul
if %errorlevel% neq 0 (
    echo Redis 服务未运行，尝试启动...
    net start Redis
) else (
    echo Redis 服务已在运行
)

REM 首先尝试停止可能正在运行的旧 Celery 进程
echo 尝试关闭可能存在的旧 Celery 进程...
taskkill /F /FI "WINDOWTITLE eq Celery*" /T > nul 2>&1
timeout /t 2 > nul

REM 设置环境变量
echo 设置环境变量...
set FLASK_APP=app
set CELERY_WORKER_POOL=eventlet
set PYTHONPATH=%cd%

REM 应用数据库索引和触发器
echo 正在检查和应用数据库索引和触发器...
python scripts/create_unique_index.py
if %errorlevel% neq 0 (
    echo 警告: 创建唯一索引时出现错误，但将继续启动应用
) else (
    echo 成功应用唯一索引
)

python scripts/create_triggers.py
if %errorlevel% neq 0 (
    echo 警告: 创建触发器时出现错误，但将继续启动应用
) else (
    echo 成功应用数据库触发器
)

REM 启动 Flask 应用
echo 启动 Flask 应用...
start "Flask App" cmd /k "call .venv\Scripts\activate.bat && python wsgi.py"

REM 等待 Flask 应用启动
timeout /t 3 > nul

REM 生成包含时间戳的唯一 Worker 名称
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a%%b)
set timestamp=%mydate%_%mytime%

REM 使用 eventlet 池和唯一名称启动 Celery worker
echo 启动 Celery Worker (使用 eventlet 池)...
start "Celery Correction Worker" cmd /k "call .venv\Scripts\activate.bat && celery -A app.tasks.celery_app:celery_app worker --loglevel=info -P eventlet -c 10 -Q correction -n worker_correction_%timestamp%@%%h"

REM 等待确保 worker 正常启动
timeout /t 3 > nul

echo 所有服务已启动!
echo 请勿关闭此窗口，关闭此窗口将终止所有服务。
echo 在浏览器中访问 http://localhost:5000 以使用应用

pause