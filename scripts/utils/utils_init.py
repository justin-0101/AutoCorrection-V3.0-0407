# Utils 工具包初始化
import os

# 确保utils目录存在
utils_dir = 'utils'
if not os.path.exists(utils_dir):
    os.makedirs(utils_dir)

# 创建空的__init__.py文件
init_file = os.path.join(utils_dir, '__init__.py')
with open(init_file, 'w', encoding='utf-8') as f:
    f.write('# Utils 工具包\n# 包含各种实用工具函数和模块\n')

print(f"已创建utils包: {init_file}") 