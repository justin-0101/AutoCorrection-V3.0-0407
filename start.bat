@echo off
echo ===== 启动系统服务 =====

REM 激活虚拟环境
echo.
echo ====== 激活虚拟环境 ======
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo 已激活虚拟环境
) else (
    echo 警告: 虚拟环境未找到，尝试使用全局Python
)

REM 设置PYTHONPATH，确保模块导入路径正确
set PYTHONPATH=%~dp0

echo.
echo ====== Redis状态 ======
echo Redis已作为系统服务运行，无需启动

echo.
echo ====== 启动Celery Worker ======
echo 将在新窗口中启动Celery Worker...
echo 请勿关闭该窗口，否则异步任务将无法处理

REM 确保设置正确的Python路径和工作目录，并且在同一虚拟环境中启动Celery
REM 使用 -P eventlet 替代 --pool=solo，并移除 --concurrency=1 (使用配置文件中的设置)
start cmd /k "cd /d %~dp0 && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) && set PYTHONPATH=%~dp0 && echo 正在启动Celery Worker... && python -m celery -A app.tasks:celery worker -P eventlet --loglevel=info -E"

echo.
echo ====== 等待Celery启动 ======
echo 等待5秒钟让Celery完成启动...
timeout /t 5

echo.
echo ====== 启动Flask应用 ======
echo 启动Flask Web应用...
python wsgi.py

echo.
echo 所有服务已停止
pause 