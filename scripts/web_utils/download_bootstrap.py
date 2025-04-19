#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
下载Bootstrap文件到本地目录的脚本
"""

import os
import sys
import requests
from pathlib import Path
import shutil

print("开始执行Bootstrap下载脚本...")

# 确保工作目录正确
ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "app" / "static"

print(f"工作目录: {ROOT_DIR}")
print(f"静态文件目录: {STATIC_DIR}")

# 创建目录
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"

CSS_DIR.mkdir(exist_ok=True, parents=True)
JS_DIR.mkdir(exist_ok=True, parents=True)

print(f"CSS目录: {CSS_DIR}")
print(f"JS目录: {JS_DIR}")

# 要下载的文件
FILES_TO_DOWNLOAD = [
    # Bootstrap CSS
    {
        "url": "https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.2.3/css/bootstrap.min.css",
        "dest": CSS_DIR / "bootstrap.min.css"
    },
    # Bootstrap CSS Map
    {
        "url": "https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.2.3/css/bootstrap.min.css.map",
        "dest": CSS_DIR / "bootstrap.min.css.map"
    },
    # Bootstrap Icons CSS
    {
        "url": "https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.11.3/font/bootstrap-icons.min.css",
        "dest": CSS_DIR / "bootstrap-icons.min.css"
    },
    # Bootstrap JS
    {
        "url": "https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.2.3/js/bootstrap.bundle.min.js",
        "dest": JS_DIR / "bootstrap.bundle.min.js"
    },
    # Bootstrap JS Map
    {
        "url": "https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/5.2.3/js/bootstrap.bundle.min.js.map",
        "dest": JS_DIR / "bootstrap.bundle.min.js.map"
    }
]

def download_file(url, dest_path):
    """下载文件到指定路径"""
    try:
        print(f"正在下载: {url}")
        print(f"保存到: {dest_path}")
        
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()  # 检查错误
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"下载完成: {dest_path}")
        return True
    except Exception as e:
        print(f"下载失败 {url}: {str(e)}")
        return False

def main():
    """主函数"""
    print("开始下载Bootstrap文件...")
    
    success_count = 0
    failed_count = 0
    
    for file_info in FILES_TO_DOWNLOAD:
        if download_file(file_info["url"], file_info["dest"]):
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\n下载完成! 成功: {success_count}, 失败: {failed_count}")
    
    if success_count > 0:
        # 修改base.html文件
        base_html = ROOT_DIR / "app" / "templates" / "base.html"
        if base_html.exists():
            # 备份
            shutil.copy2(base_html, str(base_html) + ".bak")
            print(f"已备份原始模板: {base_html}.bak")
            
            try:
                with open(base_html, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 替换CSS链接
                content = content.replace(
                    '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">',
                    '<link href="{{ url_for(\'static\', filename=\'css/bootstrap.min.css\') }}" rel="stylesheet">'
                )
                
                content = content.replace(
                    '<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">',
                    '<link href="{{ url_for(\'static\', filename=\'css/bootstrap-icons.min.css\') }}" rel="stylesheet">'
                )
                
                # 替换JS链接
                content = content.replace(
                    '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>',
                    '<script src="{{ url_for(\'static\', filename=\'js/bootstrap.bundle.min.js\') }}"></script>'
                )
                
                # 保存修改后的文件
                with open(base_html, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"已修改模板以使用本地Bootstrap文件: {base_html}")
                print("请重启Flask应用以应用更改")
            
            except Exception as e:
                print(f"修改模板时出错: {str(e)}")
                print("你可以手动修改模板文件以使用本地Bootstrap文件")
    
    print("\n如果下载失败，请手动下载文件并放入相应目录")

if __name__ == "__main__":
    main() 