#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文分析服务模块
负责作文批改结果的统计和分析
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from app.models.essay import Essay
from app.models.correction import Correction
from app.models.user import User

# 配置日志记录器
logger = logging.getLogger('app.core.correction.analysis')

class AnalysisService:
    """
    作文分析服务类
    
    负责对作文批改结果进行统计和分析：
    1. 用户作文批改历史分析
    2. 作文质量趋势分析
    3. 常见错误统计
    4. 长期进步分析
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(AnalysisService, cls).__new__(cls)
        return cls._instance
    
    def get_user_progress_report(self, user_id: int, period: str = 'month') -> Dict[str, Any]:
        """
        获取用户作文进步报告
        
        Args:
            user_id: 用户ID
            period: 时间周期，可选值：week, month, year
            
        Returns:
            Dict: 用户进步报告
        """
        try:
            # 确定时间范围
            end_date = datetime.now()
            if period == 'week':
                start_date = end_date - timedelta(days=7)
            elif period == 'month':
                start_date = end_date - timedelta(days=30)
            elif period == 'year':
                start_date = end_date - timedelta(days=365)
            else:
                # 默认为月
                start_date = end_date - timedelta(days=30)
            
            # 查询用户在指定时间段内的作文
            from app.models.db import db
            essays = Essay.query.filter(
                Essay.user_id == user_id,
                Essay.created_at >= start_date,
                Essay.created_at <= end_date,
                Essay.status == 'completed'
            ).order_by(Essay.created_at.asc()).all()
            
            if not essays:
                return {
                    "success": True,
                    "has_data": False,
                    "message": "该时间段内没有批改记录"
                }
            
            # 获取每篇作文的批改结果
            correction_data = []
            for essay in essays:
                correction = essay.get_latest_correction()
                if correction:
                    correction_data.append({
                        "essay_id": essay.id,
                        "title": essay.title,
                        "date": essay.created_at.strftime('%Y-%m-%d'),
                        "score": correction.score,
                        "content_score": correction.content_score,
                        "language_score": correction.language_score,
                        "structure_score": correction.structure_score,
                        "writing_score": correction.writing_score
                    })
            
            # 计算进步情况
            if len(correction_data) < 2:
                progress = {
                    "has_trend": False,
                    "message": "需要至少两次批改才能分析进步趋势"
                }
            else:
                first = correction_data[0]
                last = correction_data[-1]
                
                # 总分进步
                score_change = last['score'] - first['score']
                score_change_percent = round((score_change / first['score']) * 100 if first['score'] > 0 else 0, 1)
                
                # 分项得分进步
                content_change = last['content_score'] - first['content_score']
                language_change = last['language_score'] - first['language_score']
                structure_change = last['structure_score'] - first['structure_score']
                writing_change = last['writing_score'] - first['writing_score']
                
                progress = {
                    "has_trend": True,
                    "total_essays": len(correction_data),
                    "score_change": score_change,
                    "score_change_percent": score_change_percent,
                    "content_change": content_change,
                    "language_change": language_change,
                    "structure_change": structure_change,
                    "writing_change": writing_change,
                    "trend": "上升" if score_change > 0 else ("下降" if score_change < 0 else "稳定")
                }
            
            # 返回结果
            return {
                "success": True,
                "has_data": True,
                "period": period,
                "data": correction_data,
                "progress": progress,
                "stats": self._calculate_stats(correction_data)
            }
            
        except Exception as e:
            logger.error(f"获取用户进步报告异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"获取进步报告失败: {str(e)}"
            }
    
    def get_user_common_errors(self, user_id: int, limit: int = 10) -> Dict[str, Any]:
        """
        获取用户常见错误统计
        
        Args:
            user_id: 用户ID
            limit: 返回的错误数量限制
            
        Returns:
            Dict: 常见错误统计
        """
        try:
            # 查询用户的所有批改记录
            from app.models.db import db
            essays = Essay.query.filter_by(
                user_id=user_id,
                status='completed'
            ).order_by(Essay.created_at.desc()).all()
            
            if not essays:
                return {
                    "success": True,
                    "has_data": False,
                    "message": "没有批改记录"
                }
            
            # 收集所有错别字
            all_errors = []
            for essay in essays:
                correction = essay.get_latest_correction()
                if correction and correction.feedback:
                    try:
                        feedback = json.loads(correction.feedback)
                        if "错别字" in feedback and isinstance(feedback["错别字"], list):
                            for error in feedback["错别字"]:
                                if isinstance(error, dict) and "错误" in error:
                                    all_errors.append({
                                        "essay_id": essay.id,
                                        "date": essay.created_at.strftime('%Y-%m-%d'),
                                        "error": error.get("错误", ""),
                                        "correct": error.get("正确写法", ""),
                                        "context": error.get("上下文", "")
                                    })
                    except json.JSONDecodeError:
                        continue
            
            # 统计错误频率
            error_counts = {}
            for error in all_errors:
                error_text = error["error"]
                if error_text in error_counts:
                    error_counts[error_text]["count"] += 1
                    error_counts[error_text]["examples"].append({
                        "essay_id": error["essay_id"],
                        "date": error["date"],
                        "context": error["context"]
                    })
                else:
                    error_counts[error_text] = {
                        "error": error_text,
                        "correct": error["correct"],
                        "count": 1,
                        "examples": [{
                            "essay_id": error["essay_id"],
                            "date": error["date"],
                            "context": error["context"]
                        }]
                    }
            
            # 按频率排序并限制数量
            common_errors = sorted(
                list(error_counts.values()),
                key=lambda x: x["count"],
                reverse=True
            )[:limit]
            
            return {
                "success": True,
                "has_data": len(common_errors) > 0,
                "total_errors": len(all_errors),
                "unique_errors": len(error_counts),
                "common_errors": common_errors
            }
            
        except Exception as e:
            logger.error(f"获取用户常见错误异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"获取常见错误失败: {str(e)}"
            }
    
    def _calculate_stats(self, correction_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算基础统计指标
        
        Args:
            correction_data: 批改数据列表
            
        Returns:
            Dict: 统计结果
        """
        if not correction_data:
            return {
                "count": 0,
                "avg_score": 0,
                "max_score": 0,
                "min_score": 0
            }
        
        # 提取分数列表
        scores = [item['score'] for item in correction_data]
        
        # 计算统计指标
        return {
            "count": len(scores),
            "avg_score": round(sum(scores) / len(scores), 1),
            "max_score": max(scores),
            "min_score": min(scores)
        }
    
    def get_performance_by_category(self, user_id: int, category: str = 'grade_level') -> Dict[str, Any]:
        """
        按类别获取表现分析
        
        Args:
            user_id: 用户ID
            category: 分类类型，例如：grade_level, category等
            
        Returns:
            Dict: 按类别的表现分析
        """
        try:
            # 查询用户的所有完成批改的作文
            from app.models.db import db
            essays = Essay.query.filter_by(
                user_id=user_id,
                status='completed'
            ).all()
            
            if not essays:
                return {
                    "success": True,
                    "has_data": False,
                    "message": "没有批改记录"
                }
            
            # 按类别分组
            categories = {}
            for essay in essays:
                correction = essay.get_latest_correction()
                if not correction:
                    continue
                    
                # 获取分类值
                if category == 'grade_level':
                    category_value = essay.grade_level or 'unknown'
                elif category == 'category':
                    category_value = essay.category or 'unknown'
                else:
                    category_value = 'default'
                
                # 添加到对应类别
                if category_value not in categories:
                    categories[category_value] = {
                        "count": 0,
                        "total_score": 0,
                        "scores": []
                    }
                
                categories[category_value]["count"] += 1
                categories[category_value]["total_score"] += correction.score
                categories[category_value]["scores"].append(correction.score)
            
            # 计算每个类别的统计信息
            result = []
            for category_value, data in categories.items():
                avg_score = round(data["total_score"] / data["count"], 1) if data["count"] > 0 else 0
                result.append({
                    "category": category_value,
                    "count": data["count"],
                    "avg_score": avg_score,
                    "max_score": max(data["scores"]) if data["scores"] else 0,
                    "min_score": min(data["scores"]) if data["scores"] else 0
                })
            
            # 按平均分数排序
            result.sort(key=lambda x: x["avg_score"], reverse=True)
            
            return {
                "success": True,
                "has_data": True,
                "category_type": category,
                "total_essays": sum(item["count"] for item in result),
                "categories": result
            }
            
        except Exception as e:
            logger.error(f"获取类别表现分析异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"获取类别表现分析失败: {str(e)}"
            }
    
    def get_improvement_suggestions(self, user_id: int) -> Dict[str, Any]:
        """
        生成改进建议
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 包含改进建议的字典
        """
        try:
            # 获取用户的常见错误
            common_errors = self.get_user_common_errors(user_id)
            
            # 获取用户的进步报告
            progress_report = self.get_user_progress_report(user_id)
            
            # 如果没有足够的数据
            if (not common_errors.get('has_data', False) and 
                not progress_report.get('has_data', False)):
                return {
                    "success": True,
                    "has_suggestions": False,
                    "message": "没有足够的数据生成改进建议"
                }
            
            # 生成改进建议
            suggestions = []
            
            # 基于常见错误的建议
            if common_errors.get('has_data', False) and common_errors.get('common_errors'):
                errors = common_errors['common_errors'][:3]  # 取前3个常见错误
                for error in errors:
                    suggestions.append({
                        "type": "spelling",
                        "title": f"注意常见错别字: '{error['error']}'",
                        "description": f"这是您经常出现的错误，正确写法是: '{error['correct']}'。"
                    })
            
            # 基于进步报告的建议
            if progress_report.get('has_data', False) and progress_report.get('progress', {}).get('has_trend', False):
                progress = progress_report['progress']
                
                # 找出进步最少或下降最多的项
                aspects = [
                    {"name": "内容", "change": progress.get('content_change', 0)},
                    {"name": "语言", "change": progress.get('language_change', 0)},
                    {"name": "结构", "change": progress.get('structure_change', 0)},
                    {"name": "写作", "change": progress.get('writing_change', 0)}
                ]
                
                # 按变化升序排序
                aspects.sort(key=lambda x: x["change"])
                
                # 针对最弱的方面提供建议
                if aspects[0]["change"] < 0:
                    suggestions.append({
                        "type": "improvement",
                        "title": f"加强{aspects[0]['name']}方面的练习",
                        "description": f"您在{aspects[0]['name']}方面的得分有所下降，建议重点加强这一方面的能力。"
                    })
                
                # 对整体表现提供建议
                if progress.get('score_change', 0) < 0:
                    suggestions.append({
                        "type": "general",
                        "title": "作文整体水平需要提高",
                        "description": "您最近的作文得分有所下降，建议回顾之前得分较高的作文，分析成功的要素。"
                    })
                elif progress.get('score_change', 0) > 0:
                    suggestions.append({
                        "type": "encouragement",
                        "title": "继续保持良好的写作习惯",
                        "description": f"您的作文水平正在提高，进步了{abs(progress.get('score_change', 0))}分，继续保持!"
                    })
            
            # 如果没有具体建议，添加一个通用建议
            if not suggestions:
                suggestions.append({
                    "type": "general",
                    "title": "增加写作练习频率",
                    "description": "建议每周至少完成1-2篇作文练习，坚持才能看到明显的进步。"
                })
            
            return {
                "success": True,
                "has_suggestions": True,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"生成改进建议异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"生成改进建议失败: {str(e)}"
            }
