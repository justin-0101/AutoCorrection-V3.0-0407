import os

def clean_file(file_path):
    """清理文件中的空字节和控制字符"""
    try:
        # 读取文件内容，忽略错误
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 过滤掉空字节和控制字符
        cleaned_content = ''.join(c for c in content if ord(c) >= 32 or c == '\n' or c == '\t')
        
        # 写入新内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"已清理文件: {file_path}")
        return True
    except Exception as e:
        print(f"清理文件 {file_path} 时出错: {str(e)}")
        return False

def clean_directory(directory, extensions=None):
    """递归清理目录中的所有Python文件"""
    if extensions is None:
        extensions = ['.py']
    
    cleaned_files = 0
    failed_files = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 检查文件扩展名
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                if clean_file(file_path):
                    cleaned_files += 1
                else:
                    failed_files += 1
    
    print(f"目录 {directory} 清理完成，成功: {cleaned_files}，失败: {failed_files}")
    return cleaned_files, failed_files

def main():
    # 清理tasks目录中的所有Python文件
    tasks_dir = "tasks"
    services_dir = "services"
    app_dir = "app"
    
    # 直接清理特定文件
    specific_files = [
        os.path.join(tasks_dir, "correction_tasks.py"),
        os.path.join(tasks_dir, "user_tasks.py"),
        os.path.join(tasks_dir, "celery_app.py"),
        os.path.join(tasks_dir, "__init__.py"),
        os.path.join(services_dir, "ai_service.py") if os.path.exists(os.path.join(services_dir, "ai_service.py")) else None
    ]
    
    for file_path in specific_files:
        if file_path and os.path.exists(file_path):
            clean_file(file_path)
    
    # 递归清理所有目录
    directories_to_clean = [tasks_dir, services_dir, app_dir]
    for directory in directories_to_clean:
        if os.path.exists(directory) and os.path.isdir(directory):
            clean_directory(directory)
        else:
            print(f"目录不存在: {directory}")

if __name__ == "__main__":
    main() 