"""
修复批量上传路由中的try-except结构问题
"""

def fix_batch_upload_try_except():
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 读取app.py文件
        with open('app.py', 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # 查找批量上传路由的位置
        batch_upload_start = -1
        batch_upload_end = -1
        
        for i, line in enumerate(lines):
            if "@app.route('/batch_upload'" in line:
                batch_upload_start = i
            elif batch_upload_start != -1 and "@app.route('/order_history')" in line:
                batch_upload_end = i
                break
        
        if batch_upload_start == -1 or batch_upload_end == -1:
            print("无法找到批量上传路由的完整代码")
            return False
        
        # 找到问题所在的try-except结构
        fixed_lines = []
        problem_line = -1
        
        for i in range(batch_upload_start, batch_upload_end):
            line = lines[i]
            
            # 检测到有问题的try块和for循环
            if "try:" in line and "conn = sqlite3.connect" in lines[i+1]:
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
                problem_line = i
                # 添加try行
                fixed_lines.append(line)
                # 添加下一行(conn = sqlite3.connect...)
                fixed_lines.append(lines[i+1])
                # 在这里修复结构，添加一个嵌套的try块
                fixed_lines.append("            try:\n")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                i += 1  # 跳过已经添加的行
                continue
            
            # 检测for循环，需要给它前面添加except或finally
            elif problem_line != -1 and "for file in files:" in line:
                # 首先添加一个except块来关闭前面的try
                fixed_lines.append("            except Exception as e:\n")
                fixed_lines.append("                logger.error(f\"连接数据库时出错: {str(e)}\")\n")
                fixed_lines.append("                flash('连接数据库时出错，请稍后再试', 'danger')\n")
                fixed_lines.append("                return redirect(request.url)\n\n")
                # 然后添加for循环
                fixed_lines.append(line)
                continue
            
            # 对于其他行，正常添加
            fixed_lines.append(line)
        
        # 将修复好的批量上传路由代码替换回去
        updated_lines = lines[:batch_upload_start] + fixed_lines + lines[batch_upload_end:]
        
        # 写回文件
        with open('app.py', 'w', encoding='utf-8') as file:
            file.writelines(updated_lines)
        
        print("成功修复批量上传路由中的try-except结构问题!")
        return True
    except Exception as e:
        print(f"修复过程中出错: {str(e)}")
        return False

if __name__ == "__main__":
    fix_batch_upload_try_except() 