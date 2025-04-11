@echo off
chcp 65001

REM ========================================================
REM Redis Startup Script
REM ========================================================

echo [INFO] Starting Redis server...

REM 尝试启动Redis服务（如果已安装为Windows服务）
sc start redis > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Redis Windows服务已启动!
    goto :end
)

REM 如果服务未安装，直接运行Redis服务器（前提是Redis在PATH中）
echo [INFO] 尝试直接启动Redis服务器...
where redis-server > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "Redis Server" redis-server
    echo [SUCCESS] Redis服务器已在新窗口中启动!
    goto :end
)

REM 尝试在常见路径下找到并启动Redis
if exist "C:\Program Files\Redis\redis-server.exe" (
    start "Redis Server" "C:\Program Files\Redis\redis-server.exe"
    echo [SUCCESS] Redis服务器已在新窗口中启动!
    goto :end
)

if exist "C:\redis\redis-server.exe" (
    start "Redis Server" "C:\redis\redis-server.exe"
    echo [SUCCESS] Redis服务器已在新窗口中启动!
    goto :end
)

echo [ERROR] Redis未找到或无法启动，系统可能无法正常工作！
echo 请确保Redis已安装并将其添加到系统PATH中。
echo 你可以从 https://github.com/tporadowski/redis/releases 下载Windows版Redis

:end
echo.
echo 按任意键继续...
pause > nul 