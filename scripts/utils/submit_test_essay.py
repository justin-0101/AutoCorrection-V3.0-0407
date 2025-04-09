#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提交测试作文的脚本
"""

import os
import sys

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
os.chdir(project_root)
sys.path.insert(0, project_root)

from app import create_app
from app.core.correction.correction_service import CorrectionService

def main():
    """提交测试作文"""
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        correction_service = CorrectionService()
        
        # 测试作文内容
        user_id = 1  # 测试用户ID
        title = "测试作文 - 我的理想"
        content = """
        每个人都有自己的理想。有的人想成为科学家，有的人想成为医生，而我的理想是成为一名教师。
        
        教师是一个崇高的职业。他们不仅传授知识，更重要的是培养学生的品格和价值观。我的语文老师就是我的榜样，
        她不仅教会了我们如何写作和阅读，还教会了我们如何做人。
        
        成为一名教师，我可以影响更多的年轻人，帮助他们找到自己的人生方向。虽然这个职业可能不会带来很高的收入，
        但能够看到学生们在知识的海洋中不断成长，这种成就感是无价的。
        
        为了实现这个理想，我会努力学习，提高自己的知识水平和教学能力。我相信，只要坚持不懈，终有一天我的理想
        会成为现实。
        """
        
        # 提交作文
        result = correction_service.submit_essay(
            user_id=user_id,
            title=title,
            content=content,
            grade='junior'
        )
        
        # 打印结果
        print("\n提交作文结果:")
        print(f"状态: {result['status']}")
        print(f"消息: {result['message']}")
        if result['status'] == 'success':
            print(f"作文ID: {result['essay_id']}")
            print(f"任务ID: {result['task_id']}")

if __name__ == "__main__":
    main() 