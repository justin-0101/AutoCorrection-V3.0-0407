import sqlite3
from datetime import datetime
from flask import session, redirect, url_for, render_template, request, flash, jsonify

class EssayHistory:
    def __init__(self, db_path='instance/essay_correction.db'):
        """初始化作文历史管理类"""
        self.db_path = db_path
        
    def get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_user_essays(self, user_id, page=1, per_page=10, search=None, sort_order='newest'):
        """获取用户的作文历史列表"""
        if not user_id:
            return [], None
            
        conn = self.get_db_connection()
        try:
            # 基本查询
            query = '''
                SELECT id, title, content, total_score, submission_time as created_at,
                    grade, content_score, language_score, structure_score, writing_score
                FROM essays
                WHERE user_id = ?
            '''
            
            params = [user_id]
            
            # 添加搜索条件
            if search:
                query += " AND (title LIKE ? OR content LIKE ?)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param])
                
            # 添加排序
            if sort_order == 'newest':
                query += " ORDER BY submission_time DESC"
            elif sort_order == 'oldest':
                query += " ORDER BY submission_time ASC"
            elif sort_order == 'highest':
                query += " ORDER BY COALESCE(total_score, 0) DESC, submission_time DESC"
            elif sort_order == 'lowest':
                query += " ORDER BY COALESCE(total_score, 0) ASC, submission_time DESC"
            else:
                query += " ORDER BY submission_time DESC"  # 默认按最新排序
                
            # 分页
            offset = (page - 1) * per_page
            query += f" LIMIT {per_page} OFFSET {offset}"
            
            # 执行查询
            cursor = conn.execute(query, params)
            essays = [dict(row) for row in cursor.fetchall()]
            
            # 获取总数，用于分页
            count_query = '''
                SELECT COUNT(*) as total
                FROM essays
                WHERE user_id = ?
            '''
            
            count_params = [user_id]
            if search:
                count_query += " AND (title LIKE ? OR content LIKE ?)"
                count_params.extend([search_param, search_param])
                
            total = conn.execute(count_query, count_params).fetchone()['total']
            
            # 格式化日期和处理空值
            for essay in essays:
                # 格式化日期
                if 'created_at' in essay and essay['created_at']:
                    try:
                        date_str = str(essay['created_at']) 
                        if '.' in date_str:
                            date_str = date_str.split('.')[0]
                        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        essay['created_at_formatted'] = date.strftime("%Y年%m月%d日 %H:%M")
                    except (ValueError, TypeError) as e:
                        print(f"Error formatting date '{essay['created_at']}': {e}")
                        essay['created_at_formatted'] = essay['created_at']
                
                # 确保内容不会太长，进行截断显示
                if 'content' in essay and essay['content']:
                    if len(essay['content']) > 100:  # Shorter preview
                        essay['content_preview'] = essay['content'][:100] + '...'
                    else:
                        essay['content_preview'] = essay['content']
                
                # 确保数值字段不为None
                essay['total_score'] = essay.get('total_score', 0) or 0
                essay['content_score'] = essay.get('content_score', 0) or 0
                essay['language_score'] = essay.get('language_score', 0) or 0
                essay['structure_score'] = essay.get('structure_score', 0) or 0
                essay['writing_score'] = essay.get('writing_score', 0) or 0
                essay['grade'] = essay.get('grade', '未评分')
            
            # 计算分页信息
            pagination = {
                'total': total,
                'per_page': per_page,
                'current_page': page,
                'pages': (total + per_page - 1) // per_page  # 向上取整
            }
            
            return essays, pagination
            
        except sqlite3.Error as e:
            print(f"Database error in get_user_essays: {e}")
            import logging
            logging.getLogger(__name__).error(f"Database error in get_user_essays: {e}")
            return [], None
        except Exception as e:
            print(f"Unexpected error in get_user_essays: {e}")
            import logging
            logging.getLogger(__name__).error(f"Unexpected error in get_user_essays: {e}")
            return [], None
        finally:
            conn.close()
    
    def get_essay_by_id(self, essay_id, user_id=None):
        """获取单个作文信息，可选择验证所有者"""
        if not essay_id:
            return None
            
        conn = self.get_db_connection()
        try:
            query = '''
                SELECT id, user_id, title, content, word_count, submission_time, 
                    total_score, grade, content_score, language_score, structure_score, 
                    writing_score, spelling_errors, overall_assessment, content_analysis, 
                    language_analysis, structure_analysis, writing_analysis
                FROM essays
                WHERE id = ?
            '''
            
            params = [essay_id]
            
            # 如果指定了用户ID，则检查作文是否属于该用户
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
                
            essay = conn.execute(query, params).fetchone()
            
            if not essay:
                return None
                
            return dict(essay)
                
        except sqlite3.Error as e:
            print(f"Database error in get_essay_by_id: {e}")
            import logging
            logging.getLogger(__name__).error(f"Database error in get_essay_by_id: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in get_essay_by_id: {e}")
            import logging
            logging.getLogger(__name__).error(f"Unexpected error in get_essay_by_id: {e}")
            return None
        finally:
            conn.close()
    
    def delete_essay(self, essay_id, user_id):
        """删除作文及其相关结果"""
        if not essay_id or not user_id:
            return False, "参数无效"
            
        conn = self.get_db_connection()
        try:
            # 先检查作文是否属于该用户
            essay = conn.execute(
                'SELECT id FROM essays WHERE id = ? AND user_id = ?', 
                (essay_id, user_id)
            ).fetchone()
            
            if not essay:
                return False, "未找到要删除的作文或无删除权限"
                
            # 开始事务
            conn.execute('BEGIN TRANSACTION')
            
            # 删除作文记录
            conn.execute('DELETE FROM essays WHERE id = ?', (essay_id,))
            
            # 提交事务
            conn.execute('COMMIT')
            
            return True, "作文已成功删除"
                
        except sqlite3.Error as e:
            # 回滚事务
            conn.execute('ROLLBACK')
            print(f"Database error in delete_essay: {e}")
            import logging
            logging.getLogger(__name__).error(f"Database error in delete_essay: {e}")
            return False, f"数据库错误: {str(e)}"
        except Exception as e:
            # 回滚事务
            conn.execute('ROLLBACK')
            print(f"Unexpected error in delete_essay: {e}")
            import logging
            logging.getLogger(__name__).error(f"Unexpected error in delete_essay: {e}")
            return False, f"系统错误: {str(e)}"
        finally:
            conn.close()

def handle_user_history_route():
    """处理用户作文历史页面路由"""
    user_id = session.get('user_id')
    if not user_id:
        flash('请先登录', 'warning')
        return redirect(url_for('login'))
    
    # 获取分页、搜索和排序参数
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str).strip()
    sort_order = request.args.get('sort', 'newest', type=str)
    
    # 检查是否有最近批量处理的文件ID，用于高亮显示
    last_batch_id = session.pop('last_batch_essay_id', None)
    
    try:
        history_manager = EssayHistory(db_path='instance/essay_correction.db')
        result = history_manager.get_user_essays(
            user_id, 
            page=page, 
            search=search, 
            sort_order=sort_order
        )
        
        # 确保即使get_user_essays返回None也能正确处理
        if result is None:
            essays, pagination = [], None
        else:
            essays, pagination = result
        
        message = request.args.get('message')
        message_type = request.args.get('message_type', 'info')
        
        return render_template(
            'user_history.html',
            essays=essays or [], # 确保essays不为None
            pagination=pagination,
            search=search,
            sort_order=sort_order,
            message=message,
            message_type=message_type,
            last_batch_id=last_batch_id
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in handle_user_history_route: {e}")
        flash(f'加载作文历史时出错，请稍后再试', 'danger')
        return redirect(url_for('index'))

def handle_delete_essay_route():
    """处理删除作文请求"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401
        
    essay_id = request.form.get('essay_id')
    if not essay_id:
        return jsonify({'success': False, 'message': '请提供有效的作文ID'}), 400
        
    try:
        history_manager = EssayHistory(db_path='instance/essay_correction.db')
        success, message = history_manager.delete_essay(essay_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in handle_delete_essay_route: {e}")
        return jsonify({'success': False, 'message': '删除作文时出错，请稍后再试'}), 500

# Note: handle_view_result_route seems redundant now as /results/<id> exists in app.py
# If needed, it should be updated similarly to use the correct table/columns
# and call the results route instead of rendering a template itself.
# Consider removing handle_view_result_route if app.py:/results/<id> covers the functionality.

# Example of potentially removing or commenting out:
# def handle_view_result_route(essay_id):
#     """(Deprecated/Needs Review)处理查看作文结果路由"""
#     user_id = session.get('user_id')
#     if not user_id:
#         return redirect(url_for('login'))
#     
#     if not essay_id:
#         flash('无效的作文ID', 'danger')
#         return redirect(url_for('user_history'))
#     
#     # Instead of fetching data here, redirect to the main results route
#     return redirect(url_for('results', essay_id=essay_id)) 