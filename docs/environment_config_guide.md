# Linux系统环境变量配置指南

## 系统环境变量

### 必要的环境变量

| 变量名 | 说明 | 示例值 | 必需性 |
|--------|------|--------|--------|
| DATABASE_URL | 数据库连接URL | sqlite:///app.db | 必需 |
| SECRET_KEY | Flask应用密钥 | your-secret-key | 必需 |
| DEFAULT_AI_PROVIDER | 默认AI提供商 | deepseek | 必需 |

### AI服务相关环境变量

| 变量名 | 说明 | 示例值 | 必需性 |
|--------|------|--------|--------|
| DEFAULT_AI_PROVIDER | 默认AI提供商名称 | deepseek | 必需 |
| DEEPSEEK_API_KEY | DeepSeek API密钥 | sk-xxxxx | 当使用DeepSeek时必需 |
| DEEPSEEK_BASE_URL | DeepSeek API基础URL | https://api.deepseek.com/v1 | 当使用DeepSeek时必需 |
| DEEPSEEK_MODEL | DeepSeek使用的模型 | deepseek-reasoner | 当使用DeepSeek时必需 |
| OPENAI_API_KEY | OpenAI API密钥 | sk-xxxxx | 当使用OpenAI时必需 |
| ALIYUN_QIANWEN_API_KEY | 阿里千问API密钥 | sk-xxxxx | 当使用阿里千问时必需 |
| ALIYUN_QIANWEN_API_ENDPOINT | 阿里千问API端点 | https://api.example.com | 当使用阿里千问时必需 |

## 全局环境变量配置 - /etc/profile

`/etc/profile`文件用于设置系统级的环境变量，会影响所有用户。以下是配置示例：

```bash
# 设置PATH环境变量
export PATH=$PATH:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# 设置语言环境
export LANG=zh_CN.UTF-8

# 设置时区
export TZ=Asia/Shanghai

# 设置编辑器
export EDITOR=vim

# 设置Java环境（示例）
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk
export PATH=$PATH:$JAVA_HOME/bin
```

## 用户级环境变量配置 - ~/.bashrc

`~/.bashrc`文件用于设置当前用户的环境变量，只对当前用户生效。以下是配置示例：

```bash
# 设置用户自定义PATH
export PATH=$PATH:$HOME/bin:$HOME/.local/bin

# 设置别名
alias ll='ls -l'
alias la='ls -la'

# 设置提示符样式
export PS1='\u@\h:\w\$ '

# 设置历史记录大小
export HISTSIZE=1000
export HISTFILESIZE=2000

# 设置Node.js环境（示例）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # 加载nvm
```

## 使环境变量生效

1. 对于全局配置（/etc/profile），使用以下命令使其生效：
```bash
source /etc/profile
```

2. 对于用户配置（~/.bashrc），使用以下命令使其生效：
```bash
source ~/.bashrc
```

## 注意事项

1. 修改系统级配置文件（/etc/profile）需要root权限
2. 建议在修改配置文件前先备份
3. 环境变量的值应使用双引号包裹，特别是当值中包含空格时
4. PATH变量中的目录用冒号(:)分隔
5. 确保添加的路径真实存在
6. 避免在PATH中添加过多不必要的路径

## 验证配置

配置完成后，可以使用以下命令验证：

```bash
# 查看所有环境变量
env

# 查看特定环境变量
echo $PATH
echo $LANG

# 验证命令是否可用
which command_name
```

## 常见问题解决

1. 如果修改后环境变量未生效，请检查：
   - 配置文件语法是否正确
   - 是否已执行source命令
   - 用户是否有权限访问相关目录

2. 如果PATH变量配置错误导致命令无法使用：
   - 使用绝对路径执行命令
   - 通过备份的配置文件恢复
   - 使用系统默认PATH：`export PATH=/usr/local/bin:/usr/bin:/bin`