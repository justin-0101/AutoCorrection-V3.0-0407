@echo off
echo 正在检查文件变更状态...
echo =====================================
git status
echo =====================================

set /p confirm=是否继续提交？(Y/N): 
if /i not "%confirm%"=="Y" (
    echo 取消提交操作
    pause
    exit
)

echo 正在添加更改...
git add .

echo 请输入提交信息:
set /p commit_msg=

echo 正在提交更改...
git commit -m "%commit_msg%"

echo 正在推送到远程仓库...
git push

echo 完成！
pause 