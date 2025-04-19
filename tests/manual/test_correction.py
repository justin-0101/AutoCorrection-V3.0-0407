#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试创建Correction记录
"""

    from app import create_app
from app.models.essay import Essay
from app.models.correction import Correction, CorrectionStatus, CorrectionType
from app.models.db import db
    
def main():
    """测试创建Correction记录"""
    app = create_app()
    
    with app.app_context():
        print("开始测试创建Correction记录")
        # 创建新的批改记录
                correction = Correction(
            essay_id=1,
            type='ai',
            status='pending',
            is_deleted=False
                )
                
                db.session.add(correction)
        try:
            db.session.commit()
            print(f"成功创建批改记录，ID: {correction.id}")
        except Exception as e:
            db.session.rollback()
            print(f"创建批改记录失败: {str(e)}")

if __name__ == "__main__":
    main() 