#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from app import create_app
from app.models.db import db
from app.models.user import User
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus

def create_test_data():
    app = create_app()
    
    with app.app_context():
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # 创建测试用户
            user = User(
                username='test_user_' + timestamp,
                email=f'test_{timestamp}@example.com',
                is_active=True
            )
            user.set_password('test123')
            db.session.add(user)
            db.session.commit()
            
            # 创建测试作文
            essay = Essay(
                title='测试作文',
                content='这是一篇测试作文。\n\n引言部分：随着科技的发展，人工智能正在改变我们的生活方式。\n\n主体部分：首先，AI技术在教育领域的应用日益广泛。智能批改系统能够帮助教师提高工作效率，为学生提供及时的反馈。其次，在医疗领域，AI辅助诊断系统能够帮助医生更准确地诊断疾病。再次，在交通领域，自动驾驶技术正在逐步成熟。\n\n结论：人工智能的发展既带来机遇也带来挑战，我们需要理性看待并合理利用这项技术。',
                user_id=1,
                grade='高一',
                status=EssayStatus.PENDING.value
            )
            db.session.add(essay)
            db.session.commit()
            
            # 创建批改任务
            correction = Correction(
                essay_id=essay.id,
                status=CorrectionStatus.PENDING.value
            )
            db.session.add(correction)
            db.session.commit()
            
            print('测试数据创建成功！')
            print(f'用户ID: {user.id}')
            print(f'作文ID: {essay.id}')
            print(f'批改任务ID: {correction.id}')
            
        except Exception as e:
            print(f'创建测试数据时出错: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    create_test_data() 