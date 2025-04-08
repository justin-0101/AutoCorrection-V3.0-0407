import os
import sys
import re
from datetime import datetime

def find_latest_log_file():
    """查找最新的日志文件"""
    # 检查日志可能存在的目录
    search_dirs = ['.', 'logs', 'log', 'instance']
    
    log_files = []
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
            
        for file in os.listdir(search_dir):
            if file.endswith('.log') or 'log' in file:
                full_path = os.path.join(search_dir, file)
                if os.path.isfile(full_path):
                    log_files.append((full_path, os.path.getmtime(full_path)))
    
    # 按修改时间排序，最新的在前
    log_files.sort(key=lambda x: x[1], reverse=True)
    
    if not log_files:
        print("未找到日志文件")
        return None
    
    print(f"找到以下日志文件:")
    for i, (file, mtime) in enumerate(log_files[:5]):  # 只显示前5个
        print(f"{i+1}. {file} - {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 返回最新的日志文件
    return log_files[0][0]

def read_log_content(log_file, lines=1000):
    """读取日志文件内容"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.readlines()
        
        # 只保留最后指定行数
        log_content = log_content[-lines:]
        return log_content
    except Exception as e:
        print(f"读取日志文件出错: {str(e)}")
        return []

def search_ai_response(log_content):
    """搜索AI响应内容"""
    response_start = None
    response_content = []
    collecting = False
    
    for i, line in enumerate(log_content):
        if "【AI原始返回内容】前1000字符" in line and not collecting:
            response_start = i
            collecting = True
            response_content.append(line)
        elif collecting and ("【AI" in line or "===" in line) and not any(x in line for x in ["【AI原始返回内容】", "【AI返回内容】"]):
            collecting = False
            break
        elif collecting:
            response_content.append(line)
    
    return response_content

def main():
    # 查找最新日志文件
    log_file = find_latest_log_file()
    if not log_file:
        return
    
    print(f"\n使用最新日志文件: {log_file}")
    print(f"最后修改时间: {datetime.fromtimestamp(os.path.getmtime(log_file)).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 读取日志内容
    log_content = read_log_content(log_file)
    if not log_content:
        return
    
    print(f"读取了{len(log_content)}行日志内容")
    
    # 查找所有与AI评分相关的行
    ai_lines = [line for line in log_content if "【AI" in line]
    if ai_lines:
        print(f"\n找到{len(ai_lines)}行AI评分相关日志")
        print("\n==== AI评分关键信息 ====")
        for line in ai_lines[:20]:  # 显示前20行
            print(line.strip())
    
    # 搜索AI响应
    ai_response = search_ai_response(log_content)
    if ai_response:
        print("\n====== AI响应内容 ======")
        for line in ai_response:
            print(line.strip())
    else:
        print("\n未找到AI原始返回内容")
        
        # 尝试直接搜索AI返回内容相关的行
        content_lines = [line for line in log_content if any(x in line for x in ["返回内容", "AI原始", "JSON解析"])]
        if content_lines:
            print("\n找到相关AI返回内容的线索:")
            for line in content_lines[-20:]:  # 显示最后20行
                print(line.strip())
        
        # 尝试查找是否使用了备用结果
        fallback_lines = [line for line in log_content if "【使用备用评分结果】" in line or "使用备用" in line]
        if fallback_lines:
            print("\n检测到使用了备用评分结果:")
            for line in fallback_lines:
                print(line.strip())
            
            # 查找备用结果处理完成的信息
            complete_lines = [line for line in log_content if "【备用结果处理完成】" in line or "备用结果" in line]
            for line in complete_lines:
                print(line.strip())
    
    # 查找错误信息
    error_lines = [line for line in log_content if "错误" in line or "ERROR" in line or "error" in line.lower() or "exception" in line.lower()]
    if error_lines:
        print("\n====== 错误信息 ======")
        for line in error_lines[-15:]:  # 显示最后15条错误
            print(line.strip())

if __name__ == "__main__":
    main() 