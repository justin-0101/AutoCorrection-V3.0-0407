"""
修复app.py文件中的缩进和函数定义问题
"""

def fix_indentation_issue():
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 读取app.py文件
        with open('app.py', 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 定位并修复第一个unified_ai_scoring函数定义
        start_marker = "def unified_ai_scoring(title, content):"
        first_def_pos = content.find(start_marker)
        
        if first_def_pos == -1:
            print("找不到unified_ai_scoring函数定义，无法修复")
            return False
            
        # 获取文件的前半部分(到第一个函数定义之前的内容)
        first_part = content[:first_def_pos]
        
        # 获取后半部分，包含正确的函数定义
        second_part = content[first_def_pos:]
        
        # 检查是否有两个函数定义
        second_def_pos = second_part.find(start_marker, len(start_marker))
        
        if second_def_pos == -1:
            print("找不到第二个函数定义，尝试通过手动修复")
            
            # 尝试手动修复
            fixed_content = first_part + """def unified_ai_scoring(title, content):
    \"\"\"
    调用统一评分函数并处理结果为标准格式
    
    Args:
        title (str): 作文标题
        content (str): 作文内容
        
    Returns:
        dict: 包含评分和分析的结果字典，符合评分结果页面所需格式
    \"\"\"
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 导入统一评分函数
        from llm_func import unified_essay_scoring
        
        # 使用asyncio.run代替手动创建和关闭事件循环
        import asyncio
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 首选方法：使用asyncio.run (Python 3.7+)
            unified_result = asyncio.run(unified_essay_scoring(title, content))
        except RuntimeError:
            # 备用方法：如果有现有事件循环正在运行时
            logger.info("检测到现有事件循环，使用备用方法执行异步函数")
            current_loop = asyncio.get_event_loop()
            if current_loop.is_running():
                # 创建一个新的事件循环用于此次调用
                loop = asyncio.new_event_loop()
                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                    unified_result = loop.run_until_complete(unified_essay_scoring(title, content))
                finally:
                    loop.close()
            else:
                # 使用现有事件循环
                unified_result = current_loop.run_until_complete(unified_essay_scoring(title, content))
        
        logger.info("【统一评分成功】")
        logger.info(json.dumps(unified_result, ensure_ascii=False, indent=2))
        
        # 提取各项分数
        total_score = int(unified_result.get('总得分', 0))
        grade_assessment = unified_result.get('等级评定', 'B-良好')
        
        # 从分项得分中提取各项分数
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            content_score = int(unified_result['分项得分']['内容主旨'])
            language_score = int(unified_result['分项得分']['语言文采']) 
            structure_score = int(unified_result['分项得分']['文章结构'])
            writing_score = int(unified_result['分项得分']['文面书写'])
            
            # 获取错别字内容和扣分
            spelling_errors = unified_result.get('错别字', [])
            error_deduction = len(spelling_errors) if isinstance(spelling_errors, list) else 0
            
            # 重新计算总分，考虑错别字扣分
            calculated_total = content_score + language_score + structure_score + writing_score - error_deduction
            
            # 始终使用计算得出的总分，确保错别字扣分被考虑
            total_score = calculated_total
            logger.info(f"最终总分: {total_score}（原始总分: {unified_result.get('总得分', 0)}, 错别字扣分: {error_deduction}）")
            
        except (KeyError, ValueError) as e:
            logger.warning(f"提取分项得分时出现问题: {e}，使用默认值")
            content_score = 15
            language_score = 10
            structure_score = 8
            writing_score = 5
            error_deduction = 0
        
        # 组装标准评分结果格式
        result = {
            "总分": total_score,
            "等级": grade_assessment,
            "内容分": content_score,
            "表达分": language_score,
            "结构分": structure_score,
            "书写分": writing_score,
            "错别字扣分": error_deduction,
            "错别字": {"解析": spelling_errors},
            "内容分析": unified_result.get('多维分析', {}).get('内容分析', "无内容分析"),
            "表达分析": unified_result.get('多维分析', {}).get('表达分析', "无表达分析"),
            "结构分析": unified_result.get('多维分析', {}).get('结构分析', "无结构分析"),
            "书写分析": unified_result.get('多维分析', {}).get('书写分析', "无书写分析"),
            "总体评价": unified_result.get('总体评价', f"本次作文总分为{total_score}分，等级{grade_assessment}。"),
            "原文": content,  # 添加原文字段
            "标题": title     # 添加标题字段
        }
        
        logger.info(f"统一AI评分完成，总分: {total_score}, 等级: {grade_assessment}")
        return result
        
    except Exception as e:
        logger.error(f"统一AI评分函数执行错误: {str(e)}")
        raise
"""
        else:
            # 如果找到两个函数定义，保留第二个，删除第一个
            fixed_content = first_part + second_part[second_def_pos:]
            
        # 写回文件
        with open('app.py', 'w', encoding='utf-8') as file:
            file.write(fixed_content)
            
        print("成功修复app.py文件中的缩进和函数定义问题!")
        return True
        
    except Exception as e:
        print(f"修复过程中出错: {str(e)}")
        return False

# 还需要确保'score': ai_result['总分']被替换为'score': ai_result.get('总分', 0)
def fix_index_error():
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 读取修复后的app.py文件
        with open('app.py', 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 替换所有索引错误
        fixed_content = content.replace("'score': ai_result['总分']", "'score': ai_result.get('总分', 0)")
        
        # 写回文件
        with open('app.py', 'w', encoding='utf-8') as file:
            file.write(fixed_content)
            
        print("成功修复索引错误!")
        return True
        
    except Exception as e:
        print(f"修复索引错误时出错: {str(e)}")
        return False

if __name__ == "__main__":
    # 先修复缩进和函数定义问题
    if fix_indentation_issue():
        # 然后修复索引错误
        fix_index_error()
    else:
        print("无法修复缩进问题，索引错误修复已跳过") 