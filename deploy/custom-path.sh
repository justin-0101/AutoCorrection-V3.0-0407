#!/bin/bash

# 设置基本命令路径
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH

# 设置语言环境
export LANG=en_US.UTF-8

# 设置时区
export TZ=Asia/Shanghai

# 设置命令别名
alias ls='ls --color=auto'
alias ll='ls -l'
alias la='ls -la'

# 确保命令搜索路径正确
hash -r