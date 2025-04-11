import os

print('修复数据库连接问题')

base_dir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(base_dir, 'instance')
db_path = os.path.join(instance_dir, 'essay_correction.db')

print(f'数据库路径: {db_path}')

if not os.path.exists(instance_dir):
    print(f'创建instance目录: {instance_dir}')
    os.makedirs(instance_dir)
else:
    print(f'instance目录已存在: {instance_dir}')

if not os.path.exists(db_path):
    print(f'数据库文件不存在，创建空文件: {db_path}')
    open(db_path, 'a').close()
else:
    print(f'数据库文件已存在: {db_path}')

print('修复完成，请尝试重新运行 python check_tasks_status.py')