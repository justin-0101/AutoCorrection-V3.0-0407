import os
import shutil
import datetime
import zipfile
from pathlib import Path

def create_backup():
    """创建应用程序的安全备份"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_dir = f"backup-{timestamp}"
    backup_zip = f"AutoCorrection-V2.0-Backup-{timestamp}.zip"
    
    # 创建备份目录
    os.makedirs(backup_dir, exist_ok=True)
    
    # 复制核心文件
    core_files = [
        "app.py", 
        "user_history.py", 
        "user_auth.py", 
        "user_profile.py", 
        "llm_func.py", 
        "ai_correction_config.py", 
        "tasks.py"
    ]
    
    print(f"开始备份核心文件到 {backup_dir} 目录")
    for file in core_files:
        if os.path.exists(file):
            try:
                shutil.copy2(file, os.path.join(backup_dir, file))
                print(f"已复制文件: {file}")
            except Exception as e:
                print(f"无法复制文件 {file}: {e}")
    
    # 复制templates目录
    if os.path.exists("templates"):
        try:
            template_backup = os.path.join(backup_dir, "templates")
            os.makedirs(template_backup, exist_ok=True)
            for item in os.listdir("templates"):
                src = os.path.join("templates", item)
                dst = os.path.join(template_backup, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    print(f"已复制模板文件: {item}")
                else:
                    shutil.copytree(src, dst)
                    print(f"已复制模板目录: {item}")
        except Exception as e:
            print(f"无法复制templates目录: {e}")
    
    # 压缩备份目录
    try:
        print(f"创建ZIP压缩包: {backup_zip}")
        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, backup_dir))
    except Exception as e:
        print(f"创建ZIP压缩包失败: {e}")
    
    # 删除临时备份目录
    try:
        shutil.rmtree(backup_dir)
        print(f"临时备份目录已清理")
    except Exception as e:
        print(f"清理临时备份目录失败: {e}")
    
    print("备份完成!")
    print(f"备份文件位置: {os.path.abspath(backup_zip)}")

if __name__ == "__main__":
    print("==== 创建AutoCorrection系统安全备份 ====")
    create_backup()
    print("备份过程完成，请在停止Flask应用后执行本备份脚本。") 