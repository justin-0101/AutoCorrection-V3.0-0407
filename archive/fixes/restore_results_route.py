"""
恢复results路由到当前的app.py文件中
"""

def restore_results_route():
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # results路由的代码
        results_route_code = """
# 展示评分结果
@app.route('/results')
@app.route('/results/<int:essay_id>')
def results(essay_id=None):
    \"\"\"评分结果页面，支持从session或URL参数获取essay_id\"\"\"
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 优先从URL参数获取essay_id
        if essay_id is None:
            # 如果URL没有提供ID，则尝试从session获取
            essay_id = session.get('essay_id')
            logger.info(f"从 session 获取 essay_id: {essay_id}")
        else:
            logger.info(f"从 URL 获取 essay_id: {essay_id}")

        if not essay_id:
            flash('找不到作文ID，请重新提交作文或通过历史记录访问', 'danger')
            return redirect(url_for('correction'))
            
        # 从数据库加载作文信息和评分结果
        conn = sqlite3.connect('instance/essay_correction.db')
        cursor = conn.cursor()
        cursor.execute(\"\"\"
            SELECT id, user_id, title, content, submission_time, word_count, 
                total_score, grade, content_score, language_score, structure_score, 
                writing_score, spelling_errors, overall_assessment, content_analysis, 
                language_analysis, structure_analysis, writing_analysis
            FROM essays
            WHERE id = ?
        \"\"\", (essay_id,))
        essay = cursor.fetchone()
        conn.close()
        
        if not essay:
            flash('作文不存在', 'danger')
            return redirect(url_for('correction'))
            
        # 获取所有字段
        id, user_id, title, content, submission_time, word_count, total_score, \\
        grade, content_score, language_score, structure_score, writing_score, \\
        spelling_errors, overall_assessment, content_analysis, language_analysis, \\
        structure_analysis, writing_analysis = essay
        
        # 记录标题信息
        logger.info(f"获取到的作文标题: '{title}'")
        
        # 如果标题为空，使用默认标题
        if not title or title.strip() == '':
            title = "无标题作文"
            logger.info(f"使用默认标题: '{title}'")
        
        # 检查是否有错别字数据，保证有解析字段
        if spelling_errors:
            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
                # 解析JSON格式的错别字数据
                spelling_errors = json.loads(spelling_errors)
                logger.info(f"错别字数据: {spelling_errors}")
            except:
                spelling_errors = {"解析": []}
        else:
            spelling_errors = {"解析": []}
            
        # 准备传递给模板的数据
        logger.info(f"将标题 '{title}' 传递到模板")
        return render_template('results.html',
                            id=id,
                            user_id=user_id,
                            title=title,  # 确保标题传递到模板
                            content=content,
                            submission_time=submission_time,
                            word_count=word_count,
                            total_score=total_score,
                            grade=grade,
                            content_score=content_score,
                            language_score=language_score,
                            structure_score=structure_score,
                            writing_score=writing_score,
                            spelling_errors=spelling_errors,
                            overall_assessment=overall_assessment,
                            content_analysis=content_analysis,
                            language_analysis=language_analysis,
                            structure_analysis=structure_analysis,
                            writing_analysis=writing_analysis)
    
    except Exception as e:
        logger.error(f"加载结果页面出错: {str(e)}")
        flash('加载结果出错，请稍后再试', 'danger')
        return redirect(url_for('correction'))
"""
        
        # 读取当前app.py文件
        with open('app.py', 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 检查结果路由是否已存在
        if "@app.route('/results')" in content:
            print("results路由已经存在于当前文件中，跳过...")
            return True
        
        # 找到合适的插入位置
        # 我们将在correction路由后面插入
        correction_pos = content.find("@app.route('/correction'")
        if correction_pos == -1:
            # 如果找不到correction路由，尝试在order_history路由前插入
            order_history_pos = content.find("@app.route('/order_history')")
            if order_history_pos == -1:
                print("找不到合适的插入位置！")
                return False
            
            # 找到order_history路由前面的换行符
            insert_pos = content.rfind("\n\n", 0, order_history_pos)
            if insert_pos == -1:
                insert_pos = content.rfind("\n", 0, order_history_pos)
        else:
            # 找到correction路由后面对应的函数结束的位置
            function_start = content.find("def correction():", correction_pos)
            if function_start == -1:
                print("找不到correction函数定义！")
                return False
            
            # 寻找correction函数的结束位置
            # 我们假设函数以"return"语句结束，之后是新的路由或函数
            returns = content.find("return ", function_start)
            if returns == -1:
                print("找不到correction函数的return语句！")
                return False
            
            # 找到return后的换行符，然后再找下一个换行符
            first_newline = content.find("\n", returns)
            if first_newline == -1:
                print("找不到return语句后的换行符！")
                return False
            
            # 寻找函数结束后的空行
            insert_pos = content.find("\n\n", first_newline)
            if insert_pos == -1:
                # 如果找不到两个连续的换行符，就在最近的换行符后插入
                insert_pos = first_newline
        
        # 插入results路由代码
        updated_content = content[:insert_pos] + results_route_code + content[insert_pos:]
        
        # 写回app.py文件
        with open('app.py', 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        print("成功恢复results路由!")
        return True
    except Exception as e:
        print(f"恢复过程中出错: {str(e)}")
        return False

if __name__ == "__main__":
    restore_results_route() 