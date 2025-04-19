@echo off
echo 启动批改结果同步监控服务 (60秒检查间隔)
echo ===================================

:: 设置Python环境
set PYTHONPATH=%~dp0..\..\
cd %~dp0..\..

:: 启动监控服务
python fix_correction_sync.py -m -i 60

echo 如果监控服务被中断，请再次运行此脚本
pause 