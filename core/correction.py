"""
作文批改核心模块
处理作文的批改和评分流程
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple

from services.ai_service import AIService
from app.models.essay import Essay
from database.db_manager import db_manager

# 获取logger
logger = logging.getLogger(__name__)

class CorrectionService:
    """作文批改服务"""
    
    def __init__(self, ai_service=None):
        """初始化批改服务
        
        Args:
            ai_service: AI服务实例，如果为None则创建新实例
        """
        self.ai_service = ai_service or AIService()
    
    def correct_essay(self, essay_text: str, title: str = None, user_id: int = None, 
                     grade: str = None, save_result: bool = True) -> Dict[str, Any]:
        """批改作文
        
        Args:
            essay_text: 作文内容
            title: 作文标题
            user_id: 用户ID
            grade: 作文等级（小学/初中/高中）
            save_result: 是否保存结果到数据库
            
        Returns:
            Dict: 批改结果
        """
        start_time = time.time()
        logger.info(f"开始批改作文: {title or '无标题'}")
        
        # 计算字数
        word_count = len(essay_text.split())
        
        # 调用AI服务批改作文
        correction_result = self.ai_service.correct_essay(
            essay_text=essay_text,
            title=title,
            grade=grade
        )
        
        # 检查批改是否成功
        if not correction_result.get('success', False):
            logger.error(f"作文批改失败: {correction_result.get('error', '未知错误')}")
            return {
                "status": "error",
                "message": "批改失败，请稍后再试",
                "error": correction_result.get('error', '未知错误'),
                "error_type": correction_result.get('error_type', 'UnknownError')
            }
        
        # 计算处理时间
        processing_time = time.time() - start_time
        logger.info(f"作文批改完成，耗时: {processing_time:.2f}秒")
        
        # 准备返回结果
        result = {
            "status": "success",
            "title": title,
            "original_text": essay_text,
            "corrected_text": correction_result.get('corrected_text', ''),
            "score": correction_result.get('score', {}),
            "feedback": correction_result.get('feedback', {}),
            "errors": correction_result.get('errors', []),
            "improvement_suggestions": correction_result.get('improvement_suggestions', []),
            "word_count": correction_result.get('word_count', word_count),
            "processing_time": processing_time,
            "grade": correction_result.get('grade', ''),
            "grade_description": correction_result.get('grade_description', '')
        }
        
        # 保存结果到数据库
        if save_result and user_id:
            essay_id = self._save_correction_result(
                user_id=user_id,
                title=title,
                original_text=essay_text,
                correction_result=correction_result
            )
            result['essay_id'] = essay_id
        
        return result
    
    def _save_correction_result(self, user_id: int, title: str, 
                              original_text: str, correction_result: Dict) -> int:
        """保存批改结果到数据库
        
        Args:
            user_id: 用户ID
            title: 作文标题
            original_text: 原始作文
            correction_result: 批改结果
            
        Returns:
            int: 新创建的作文ID
        """
        try:
            # 准备数据
            score = correction_result.get('score', {})
            feedback = correction_result.get('feedback', {})
            errors = json.dumps(correction_result.get('errors', []))
            
            # 创建Essay对象
            essay = Essay(
                user_id=user_id,
                title=title,
                content=original_text,
                word_count=correction_result.get('word_count', len(original_text.split())),
                total_score=score.get('total', 0),
                content_score=score.get('content', 0),
                language_score=score.get('language', 0),
                structure_score=score.get('structure', 0),
                writing_score=score.get('writing', 0),
                grade=correction_result.get('grade', ''),
                spelling_errors=errors,
                overall_assessment=feedback.get('overall', ''),
                content_analysis=feedback.get('content', ''),
                language_analysis=feedback.get('language', ''),
                structure_analysis=feedback.get('structure', ''),
                writing_analysis=feedback.get('writing', '')
            )
            
            # 保存到数据库
            with db_manager.app.app_context():
                db_manager.db.session.add(essay)
                db_manager.db.session.commit()
                essay_id = essay.id
            
            logger.info(f"批改结果已保存至数据库，ID: {essay_id}")
            return essay_id
        
        except Exception as e:
            logger.error(f"保存批改结果失败: {str(e)}")
            # 使用原生SQL作为备用方案
            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO essays (
                            user_id, title, content, submission_time, word_count,
                            total_score, content_score, language_score, structure_score,
                            writing_score, grade, spelling_errors, overall_assessment,
                            content_analysis, language_analysis, structure_analysis,
                            writing_analysis
                        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, title, original_text, 
                        correction_result.get('word_count', len(original_text.split())),
                        score.get('total', 0), score.get('content', 0),
                        score.get('language', 0), score.get('structure', 0),
                        score.get('writing', 0), correction_result.get('grade', ''),
                        errors, feedback.get('overall', ''),
                        feedback.get('content', ''), feedback.get('language', ''),
                        feedback.get('structure', ''), feedback.get('writing', '')
                    ))
                    essay_id = cursor.lastrowid
                
                logger.info(f"批改结果已通过原生SQL保存至数据库，ID: {essay_id}")
                return essay_id
            except Exception as e2:
                logger.error(f"通过原生SQL保存批改结果也失败: {str(e2)}")
                return 0
    
    def get_essay_by_id(self, essay_id: int) -> Optional[Dict]:
        """通过ID获取作文批改结果
        
        Args:
            essay_id: 作文ID
            
        Returns:
            Dict: 作文批改结果，如果不存在则返回None
        """
        try:
            # 尝试使用ORM
            with db_manager.app.app_context():
                essay = Essay.query.get(essay_id)
                
                if not essay:
                    return None
                
                # 解析JSON字段
                try:
                    errors = json.loads(essay.spelling_errors) if essay.spelling_errors else []
                except:
                    errors = []
                
                return {
                    "essay_id": essay.id,
                    "user_id": essay.user_id,
                    "title": essay.title,
                    "original_text": essay.content,
                    "submission_time": essay.submission_time,
                    "word_count": essay.word_count,
                    "score": {
                        "total": essay.total_score,
                        "content": essay.content_score,
                        "language": essay.language_score,
                        "structure": essay.structure_score,
                        "writing": essay.writing_score
                    },
                    "grade": essay.grade,
                    "feedback": {
                        "overall": essay.overall_assessment,
                        "content": essay.content_analysis,
                        "language": essay.language_analysis,
                        "structure": essay.structure_analysis,
                        "writing": essay.writing_analysis
                    },
                    "errors": errors
                }
        except Exception as e:
            logger.error(f"通过ORM获取作文批改结果失败: {str(e)}")
            
            # 使用原生SQL作为备用方案
            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM essays WHERE id = ?
                    """, (essay_id,))
                    essay = cursor.fetchone()
                    
                    if not essay:
                        return None
                    
                    # 解析JSON字段
                    try:
                        errors = json.loads(essay['spelling_errors']) if essay['spelling_errors'] else []
                    except:
                        errors = []
                    
                    return {
                        "essay_id": essay['id'],
                        "user_id": essay['user_id'],
                        "title": essay['title'],
                        "original_text": essay['content'],
                        "submission_time": essay['submission_time'],
                        "word_count": essay['word_count'],
                        "score": {
                            "total": essay['total_score'],
                            "content": essay['content_score'],
                            "language": essay['language_score'],
                            "structure": essay['structure_score'],
                            "writing": essay['writing_score']
                        },
                        "grade": essay['grade'],
                        "feedback": {
                            "overall": essay['overall_assessment'],
                            "content": essay['content_analysis'],
                            "language": essay['language_analysis'],
                            "structure": essay['structure_analysis'],
                            "writing": essay['writing_analysis']
                        },
                        "errors": errors
                    }
            except Exception as e2:
                logger.error(f"通过原生SQL获取作文批改结果也失败: {str(e2)}")
                return None
    
    def get_user_essays(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict]:
        """获取用户的作文批改历史
        
        Args:
            user_id: 用户ID
            limit: 结果数量限制
            offset: 结果偏移量
            
        Returns:
            List[Dict]: 作文批改历史列表
        """
        try:
            # 尝试使用ORM
            with db_manager.app.app_context():
                essays = Essay.query.filter_by(user_id=user_id) \
                               .order_by(Essay.submission_time.desc()) \
                               .limit(limit).offset(offset).all()
                
                result = []
                for essay in essays:
                    result.append({
                        "essay_id": essay.id,
                        "title": essay.title,
                        "submission_time": essay.submission_time,
                        "total_score": essay.total_score,
                        "grade": essay.grade,
                        "word_count": essay.word_count
                    })
                    
                return result
        except Exception as e:
            logger.error(f"通过ORM获取用户作文历史失败: {str(e)}")
            
            # 使用原生SQL作为备用方案
            try:
                with db_manager.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT id, title, submission_time, total_score, grade, word_count
                        FROM essays 
                        WHERE user_id = ?
                        ORDER BY submission_time DESC
                        LIMIT ? OFFSET ?
                    """, (user_id, limit, offset))
                    
                    result = []
                    for row in cursor.fetchall():
                        result.append({
                            "essay_id": row['id'],
                            "title": row['title'],
                            "submission_time": row['submission_time'],
                            "total_score": row['total_score'],
                            "grade": row['grade'],
                            "word_count": row['word_count']
                        })
                        
                    return result
            except Exception as e2:
                logger.error(f"通过原生SQL获取用户作文历史也失败: {str(e2)}")
                return []

# 创建全局批改服务实例
correction_service = CorrectionService()
