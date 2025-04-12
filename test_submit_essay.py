#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试提交作文功能
"""

from app import create_app
from app.core.correction.correction_service import CorrectionService
from app.models.essay import Essay
from app.models.correction import Correction
from app.models.db import db

def test_submit_essay():
    """测试提交作文功能"""
    app = create_app()
    
    with app.app_context():
        print("开始测试提交作文功能")
        
        # 创建批改服务实例
        correction_service = CorrectionService()
        
        # 提交作文
        result = correction_service.submit_essay(
            user_id=1,  # 使用管理员用户ID
            title="测试作文 - 自动批改修复测试",
            content="这是一篇测试作文，用于测试自动批改功能的修复。我们需要确保系统能够正确处理作文提交和批改流程。",
            grade="junior"
        )
        
        print(f"提交结果: {result}")
        
        if result.get('status') == 'success':
            # 查询作文和批改记录
            essay_id = result.get('essay_id')
            essay = Essay.query.get(essay_id)
            correction = Correction.query.filter_by(essay_id=essay_id).first()
            
            print(f"作文ID: {essay.id}, 标题: {essay.title}, 状态: {essay.status}")
            
            if correction:
                print(f"批改记录ID: {correction.id}, 状态: {correction.status}, 是否已删除: {correction.is_deleted}")
            else:
                print("未找到批改记录")
        else:
            print(f"提交失败: {result.get('message')}")

if __name__ == "__main__":
    test_submit_essay() 