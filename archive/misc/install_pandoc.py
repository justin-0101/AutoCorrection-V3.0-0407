import os
import sys
import subprocess
import platform
import tempfile
from urllib.request import urlretrieve
import zipfile
import shutil

def is_pandoc_installed():
    """检查Pandoc是否已安装"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        result = subprocess.run(['pandoc', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        # 检查当前目录中是否有Pandoc
        pandoc_path = os.path.join(os.getcwd(), 'pandoc', 'pandoc.exe')
        if os.path.exists(pandoc_path):
            return True
        return False

def download_pandoc():
    """下载并安装Pandoc到当前项目目录"""
    system = platform.system()
    if system == 'Windows':
        # 使用32位版本的Pandoc
        url = "https://github.com/jgm/pandoc/releases/download/3.1.12.1/pandoc-3.1.12.1-windows-i386.zip"
        print("正在下载Pandoc (32位版本)...")
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "pandoc.zip")
        urlretrieve(url, zip_path)
        
        print("正在解压Pandoc...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 从解压的目录中找到pandoc.exe
        pandoc_exe = None
        for root, dirs, files in os.walk(temp_dir):
            if "pandoc.exe" in files:
                pandoc_exe = os.path.join(root, "pandoc.exe")
                break
        
        if not pandoc_exe:
            print("在解压后的文件中未找到pandoc.exe")
            return False
        
        # 创建本地Pandoc目录
        target_dir = os.path.join(os.getcwd(), 'pandoc')
        
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(pandoc_exe, os.path.join(target_dir, 'pandoc.exe'))
            
            print(f"Pandoc已安装到项目目录: {target_dir}")
            
            # 清理临时文件
            shutil.rmtree(temp_dir)
            return True
        except Exception as e:
            print(f"安装Pandoc时出错: {e}")
            return False
    elif system == 'Darwin':  # macOS
        print("在macOS上, 请使用以下命令安装Pandoc:")
        print("brew install pandoc")
        return False
    elif system == 'Linux':
        print("在Linux上, 请使用以下命令安装Pandoc:")
        print("sudo apt-get install pandoc")
        return False
    else:
        print(f"不支持的操作系统: {system}")
        return False

def main():
    if is_pandoc_installed():
        print("Pandoc已安装。")
    else:
        print("Pandoc未安装。正在尝试安装...")
        if download_pandoc():
            print("Pandoc安装成功!")
            print("请重新启动应用程序以使更改生效。")
        else:
            print("Pandoc安装失败。请手动安装: https://pandoc.org/installing.html")

if __name__ == "__main__":
    main() 