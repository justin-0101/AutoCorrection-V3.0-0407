import os

print('�޸����ݿ���������')

base_dir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(base_dir, 'instance')
db_path = os.path.join(instance_dir, 'essay_correction.db')

print(f'���ݿ�·��: {db_path}')

if not os.path.exists(instance_dir):
    print(f'����instanceĿ¼: {instance_dir}')
    os.makedirs(instance_dir)
else:
    print(f'instanceĿ¼�Ѵ���: {instance_dir}')

if not os.path.exists(db_path):
    print(f'���ݿ��ļ������ڣ��������ļ�: {db_path}')
    open(db_path, 'a').close()
else:
    print(f'���ݿ��ļ��Ѵ���: {db_path}')

print('�޸���ɣ��볢���������� python check_tasks_status.py')