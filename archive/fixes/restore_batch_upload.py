"""
从备份文件中恢复批量上传路由到app.py
"""

def restore_batch_upload_route():
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 从备份文件中读取batch_upload路由的代码
        with open('backup/app.py', 'r', encoding='utf-8') as file:
            backup_content = file.read()
        
        # 定位批量上传路由的开始和结束
        start_marker = "# 批量上传作文路由\n@app.route('/batch_upload', methods=['GET', 'POST'])"
        end_marker = "# 展示评分结果"
        
        if start_marker not in backup_content or end_marker not in backup_content:
            print("无法在备份文件中找到批量上传路由的完整代码")
            return False
        
        # 提取批量上传路由的完整代码
        start_index = backup_content.find(start_marker)
        end_index = backup_content.find(end_marker, start_index)
        
        if start_index == -1 or end_index == -1:
            print("提取批量上传路由代码失败")
            return False
        
        # 批量上传路由代码(不包括结束标记)
        batch_upload_code = backup_content[start_index:end_index].strip()
        
        # 读取当前的app.py文件
        with open('app.py', 'r', encoding='utf-8') as file:
            app_content = file.read()
        
        # 检查批量上传路由是否已存在
        if "def batch_upload():" in app_content:
            print("批量上传路由已存在于app.py中")
            return True
        
        # 找到合适的插入位置 (在order_history路由之前)
        insert_marker = "# 批量上传作文路由"
        if insert_marker in app_content:
            print(f"标记 '{insert_marker}' 已存在，将替换相应的代码")
            # 找到标记后的代码段，将其替换为从备份恢复的代码
            insert_start = app_content.find(insert_marker)
            # 找到下一个路由或函数定义
            possible_ends = [
                app_content.find("# 展示评分结果", insert_start),
                app_content.find("@app.route", insert_start),
                app_content.find("def ", insert_start)
            ]
            # 过滤掉-1
            possible_ends = [x for x in possible_ends if x > 0]
            if possible_ends:
                insert_end = min(possible_ends)
                # 替换代码
                new_app_content = app_content[:insert_start] + batch_upload_code + "\n\n" + app_content[insert_end:]
            else:
                print("无法找到插入点的结束位置")
                return False
        else:
            # 找到order_history路由作为插入点
            order_history_marker = "@app.route('/order_history')"
            if order_history_marker in app_content:
                order_history_pos = app_content.find(order_history_marker)
                # 往前找到合适的插入位置（前一个路由的结束位置）
                for i in range(order_history_pos - 1, 0, -1):
                    if app_content[i:i+1] == "\n" and app_content[i+1:i+2] == "\n":
                        insert_pos = i + 1
                        break
                else:
                    # 如果没找到空行，就在order_history之前插入
                    insert_pos = app_content.rfind("\n", 0, order_history_pos) + 1
                
                # 确保插入位置是一个段落的开始
                if insert_pos > 0:
                    new_app_content = app_content[:insert_pos] + batch_upload_code + "\n\n" + app_content[insert_pos:]
                else:
                    print("无法找到合适的插入位置")
                    return False
            else:
                # 如果找不到order_history路由，尝试在文件末尾插入
                print("找不到order_history路由，将在文件末尾插入批量上传路由")
                new_app_content = app_content + "\n\n" + batch_upload_code + "\n"
        
        # 写入更新后的app.py文件
        with open('app.py', 'w', encoding='utf-8') as file:
            file.write(new_app_content)
        
        print("成功恢复批量上传路由到app.py!")
        return True
    
    except Exception as e:
        print(f"恢复批量上传路由时出错: {str(e)}")
        return False

if __name__ == "__main__":
    restore_batch_upload_route() 