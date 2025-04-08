@echo off
echo 正在添加所有更改...
git add .

echo 请输入提交信息:
set /p commit_msg=

echo 正在提交更改...
git commit -m "%commit_msg%"

echo 正在推送到远程仓库...
git push

echo 完成！
pause 