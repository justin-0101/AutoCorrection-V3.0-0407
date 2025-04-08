@echo off
cd /d "%~dp0.."
echo 开始执行备份 - %date% %time% >> logs\backup_scheduled.log

:: 检查Python虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

:: 执行备份
python "%~dp0backup_system.py" --backup-dir "D:\git-justin0101\auto-currection\AutoCorrection_Backups" >> logs\backup_scheduled.log 2>&1

echo 备份完成 - %date% %time% >> logs\backup_scheduled.log
echo. >> logs\backup_scheduled.log 