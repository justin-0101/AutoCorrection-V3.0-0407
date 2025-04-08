import os
import logging
from datetime import datetime
from utils.db_manager import db_manager
from utils.exceptions import ValidationError, DatabaseError, db_error_handler
from config.app_config import APP_CONFIG

logger = logging.getLogger('autocorrection.essay')

class Essay:
    """作文模型类，处理作文相关的数据库操作和业务逻辑"""
    
    def __init__(self, id=None, user_id=None, title=None, content=None, grade=None,
                 feedback=None, score=None, created_at=None, updated_at=None, 
                 status='pending', file_path=None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.content = content
        self.grade = grade  # 作文年级水平: primary, junior, senior, college
        self.feedback = feedback
        self.score = score
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.status = status  # pending, processing, completed, error
        self.file_path = file_path
    
    @db_error_handler
    def save(self):
        """保存作文到数据库（新建或更新）"""
        if self.id:
            # 更新现有作文
            query = """
                UPDATE essays 
                SET title=?, content=?, grade=?, feedback=?, score=?, updated_at=?, status=?, file_path=?
                WHERE id=?
            """
            params = (self.title, self.content, self.grade, self.feedback, self.score, 
                     datetime.now(), self.status, self.file_path, self.id)
            db_manager.execute_query(query, params)
            logger.info(f"已更新作文 ID: {self.id}")
            return self.id
        else:
            # 创建新作文
            query = """
                INSERT INTO essays (user_id, title, content, grade, feedback, score, 
                                  created_at, updated_at, status, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (self.user_id, self.title, self.content, self.grade, self.feedback, 
                     self.score, self.created_at, self.updated_at, self.status, self.file_path)
            self.id = db_manager.execute_query(query, params)
            logger.info(f"已创建新作文 ID: {self.id}")
            return self.id
    
    @staticmethod
    @db_error_handler
    def find_by_id(essay_id, with_content=True):
        """通过ID查找作文"""
        if with_content:
            query = "SELECT * FROM essays WHERE id = ?"
        else:
            # 不包含作文内容，适用于列表展示
            query = "SELECT id, user_id, title, grade, score, created_at, updated_at, status FROM essays WHERE id = ?"
            
        essay_data = db_manager.execute_query(query, (essay_id,), fetch_one=True)
        if not essay_data:
            return None
        return Essay(**essay_data)
    
    @staticmethod
    @db_error_handler
    def find_by_user_id(user_id, limit=50, offset=0, with_content=False):
        """查找用户的所有作文"""
        if with_content:
            query = """
                SELECT * FROM essays 
                WHERE user_id = ? 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
        else:
            query = """
                SELECT id, user_id, title, grade, score, created_at, updated_at, status 
                FROM essays 
                WHERE user_id = ? 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            
        essays_data = db_manager.execute_query(query, (user_id, limit, offset))
        return [Essay(**data) for data in essays_data]
    
    @staticmethod
    @db_error_handler
    def count_by_user_id(user_id):
        """统计用户的作文数量"""
        query = "SELECT COUNT(*) as count FROM essays WHERE user_id = ?"
        result = db_manager.execute_query(query, (user_id,), fetch_one=True)
        return result['count'] if result else 0
    
    @staticmethod
    @db_error_handler
    def delete(essay_id, user_id=None):
        """删除作文（可选：仅限指定用户的作文）"""
        if user_id:
            query = "DELETE FROM essays WHERE id = ? AND user_id = ?"
            params = (essay_id, user_id)
        else:
            query = "DELETE FROM essays WHERE id = ?"
            params = (essay_id,)
            
        result = db_manager.execute_query(query, params)
        
        # 删除相关的文件（如果存在）
        essay = Essay.find_by_id(essay_id)
        if essay and essay.file_path:
            try:
                file_path = os.path.join(APP_CONFIG['UPLOAD_FOLDER'], essay.file_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除作文文件: {file_path}")
            except Exception as e:
                logger.error(f"删除作文文件失败: {str(e)}")
        
        logger.info(f"已删除作文 ID: {essay_id}")
        return result
    
    @staticmethod
    @db_error_handler
    def search(user_id=None, keyword=None, grade=None, status=None, 
              date_from=None, date_to=None, limit=50, offset=0):
        """搜索作文"""
        query_parts = ["SELECT id, user_id, title, grade, score, created_at, updated_at, status FROM essays WHERE 1=1"]
        params = []
        
        # 构建查询条件
        if user_id:
            query_parts.append("AND user_id = ?")
            params.append(user_id)
            
        if keyword:
            query_parts.append("AND (title LIKE ? OR content LIKE ?)")
            keyword_param = f"%{keyword}%"
            params.extend([keyword_param, keyword_param])
            
        if grade:
            query_parts.append("AND grade = ?")
            params.append(grade)
            
        if status:
            query_parts.append("AND status = ?")
            params.append(status)
            
        if date_from:
            query_parts.append("AND DATE(created_at) >= DATE(?)")
            params.append(date_from)
            
        if date_to:
            query_parts.append("AND DATE(created_at) <= DATE(?)")
            params.append(date_to)
            
        # 添加排序和分页
        query_parts.append("ORDER BY created_at DESC LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        
        # 执行查询
        full_query = " ".join(query_parts)
        essays_data = db_manager.execute_query(full_query, params)
        
        return [Essay(**data) for data in essays_data]

    def to_dict(self, include_content=True):
        """将作文对象转换为字典"""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "grade": self.grade,
            "score": self.score,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "status": self.status
        }
        
        if include_content:
            result.update({
                "content": self.content,
                "feedback": self.feedback,
                "file_path": self.file_path
            })
            
        return result 