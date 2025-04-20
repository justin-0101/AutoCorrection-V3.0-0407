@echo off
title 修复的Celery启动脚本
echo 正在启动修复后的Celery worker...

REM 激活虚拟环境
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 激活虚拟环境失败，请确保虚拟环境存在且路径正确
    pause
    exit /b 1
)
echo 虚拟环境已激活

REM 设置环境变量
set PYTHONPATH=%CD%
set FLASK_APP=app

REM 运行修复的Celery启动脚本
python scripts\startup\start_celery_fix.py

pause 