@echo off
echo 启动Celery Worker (使用eventlet池)...

:: 激活虚拟环境（如果有）
if exist .venv\Scripts\activate (
    call .venv\Scripts\activate
)

:: 设置环境变量
set CELERY_WORKER_POOL=eventlet
set FLASK_APP=app

:: 启动Celery worker (使用正确的应用路径)
celery -A app.tasks.celery_app:celery_app worker --loglevel=info -P eventlet -Q correction -c 10

pause 