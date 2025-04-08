#!/bin/bash

# 作文批改系统启动脚本

# 设置工作目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "正在激活虚拟环境..."
    source venv/bin/activate
fi

# 环境变量
export FLASK_APP=app.py
export FLASK_ENV=production

# 启动参数
START_WEB=true
START_WORKERS=false
CONCURRENCY=2
PORT=5000

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            export FLASK_ENV=development
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            START_WORKERS=true
            shift
            ;;
        --workers-only)
            START_WEB=false
            START_WORKERS=true
            shift
            ;;
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --all)
            START_WEB=true
            START_WORKERS=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 启动Redis（如果需要）
if [ "$START_WORKERS" = true ]; then
    if command -v redis-server &> /dev/null; then
        echo "检查Redis服务..."
        if ! pgrep -x "redis-server" > /dev/null; then
            echo "启动Redis服务..."
            redis-server --daemonize yes
        else
            echo "Redis服务已运行"
        fi
    else
        echo "警告: Redis未安装，Celery可能无法正常工作"
    fi
fi

# 启动Web服务器
if [ "$START_WEB" = true ]; then
    echo "启动Web服务器，端口: $PORT..."
    if [ "$START_WORKERS" = true ]; then
        # 如果同时启动workers，则在后台运行web服务器
        python app.py --port $PORT &
        WEB_PID=$!
        echo "Web服务器已在后台启动，PID: $WEB_PID"
    else
        # 只启动web服务器，在前台运行
        exec python app.py --port $PORT
    fi
fi

# 启动Celery工作进程
if [ "$START_WORKERS" = true ]; then
    echo "启动Celery工作进程，并发数: $CONCURRENCY..."
    python scripts/start_workers.py --all --concurrency $CONCURRENCY
    
    # 如果启动了Web服务器，在工作进程退出后也需要关闭Web服务器
    if [ "$START_WEB" = true ] && [ -n "$WEB_PID" ]; then
        echo "关闭Web服务器..."
        kill $WEB_PID
    fi
fi 