import re

# 读取app.py文件
with open('app.py', 'r', encoding='utf-8') as file:
    content = file.read()

# 修复批量上传函数中的错误
# 将 'score': ai_result['总分'] 改为 'score': ai_result.get('总分', 0)
pattern = r"'score': ai_result\['总分'\]"
replacement = r"'score': ai_result.get('总分', 0)"
content = re.sub(pattern, replacement, content)

# 写回文件
with open('app.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("成功修复批量上传功能中的索引错误!") 