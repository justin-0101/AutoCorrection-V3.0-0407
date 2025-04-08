import sqlite3
import hashlib
import os
from datetime import datetime
from flask import session, g, redirect, url_for, render_template, request, flash
from werkzeug.security import check_password_hash, generate_password_hash

class UserProfile:
    def __init__(self, db_path='instance/essay_correction.db'):
        """初始化用户个人资料管理类"""
        self.db_path = db_path
        
    def get_db_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def get_user_by_id(self, user_id):
        """根据用户ID获取用户信息"""
        conn = self.get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        return dict(user) if user else None
        
    def get_profile_by_user_id(self, user_id):
        """获取用户个人资料"""
        conn = self.get_db_connection()
        profile = conn.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        
        if not profile:
            # 如果不存在个人资料，创建一个空的默认资料
            self.create_default_profile(user_id)
            return self.get_profile_by_user_id(user_id)
            
        return dict(profile) if profile else None
        
    def create_default_profile(self, user_id):
        """为新用户创建默认个人资料"""
        conn = self.get_db_connection()
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 获取用户信息，确保用户存在
            user = conn.execute('SELECT username, email FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not user:
                return False
                
            # 插入默认个人资料
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute('''
                INSERT INTO user_profiles (user_id, full_name, school, grade, avatar_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, '', '', '', '', now, now))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()
    
    def update_profile(self, user_id, profile_data):
        """更新用户个人资料"""
        allowed_fields = ['full_name', 'school', 'grade']
        update_data = {k: v for k, v in profile_data.items() if k in allowed_fields}
        
        if not update_data:
            return False, "没有可更新的数据"
            
        conn = self.get_db_connection()
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 构建更新语句
            set_clause = ', '.join([f"{field} = ?" for field in update_data.keys()])
            set_clause += ", updated_at = ?"
            
            # 准备参数
            params = list(update_data.values())
            params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            params.append(user_id)
            
            # 执行更新
            conn.execute(f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?", params)
            conn.commit()
            return True, "个人资料已更新"
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False, f"数据库错误: {str(e)}"
        finally:
            conn.close()
    
    def change_password(self, user_id, current_password, new_password):
        """修改用户密码"""
        if not current_password or not new_password:
            return False, "密码不能为空"
            
        if len(new_password) < 6:
            return False, "新密码长度不能少于6个字符"
            
        conn = self.get_db_connection()
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 获取当前用户信息
            user = conn.execute('SELECT password_hash FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not user:
                return False, "用户不存在"
                
            # 验证当前密码
            if not check_password_hash(user['password_hash'], current_password):
                return False, "当前密码不正确"
                
            # 更新密码
            password_hash = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password_hash = ? WHERE user_id = ?', 
                        (password_hash, user_id))
            conn.commit()
            return True, "密码已成功修改"
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False, f"数据库错误: {str(e)}"
        finally:
            conn.close()
    
    def update_last_login(self, user_id):
        """更新用户最后登录时间"""
        conn = self.get_db_connection()
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 尝试更新users表中的last_login字段
            conn.execute('UPDATE users SET last_login = ? WHERE user_id = ?', (now, user_id))
            # 如果有user_profiles表，也一并更新
            conn.execute('UPDATE user_profiles SET last_login = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error updating last login: {e}")
            return False
        finally:
            conn.close()

def handle_profile_route():
    """处理个人资料页面路由"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    profile_manager = UserProfile()
    user = profile_manager.get_user_by_id(user_id)
    profile = profile_manager.get_profile_by_user_id(user_id)
    
    message = None
    message_type = None
    
    # 处理表单提交
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'profile':
            # 处理个人资料更新
            profile_data = {
                'full_name': request.form.get('full_name', ''),
                'school': request.form.get('school', ''),
                'grade': request.form.get('grade', '')
            }
            success, message = profile_manager.update_profile(user_id, profile_data)
            message_type = 'success' if success else 'danger'
            if success:
                # 更新成功后刷新个人资料数据
                profile = profile_manager.get_profile_by_user_id(user_id)
                
        elif form_type == 'password':
            # 处理密码修改
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                message = "两次输入的密码不一致"
                message_type = 'danger'
            else:
                success, message = profile_manager.change_password(user_id, current_password, new_password)
                message_type = 'success' if success else 'danger'
    
    # 渲染模板
    return render_template('profile.html', 
                        user=user, 
                        profile=profile, 
                        message=message,
                        message_type=message_type) 