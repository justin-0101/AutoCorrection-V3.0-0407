import os, sqlite3
print('�������ݿ�����')
db_path = os.path.join('instance', 'essay_correction.db')
print(f'���ݿ�·��: {db_path}')
conn = sqlite3.connect(db_path)
print('���ӳɹ�!')
