#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查作文状态的脚本
"""

import os
import sys

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
os.chdir(project_root)
sys.path.insert(0, project_root)

from app import create_app
from app.models.essay import Essay
from app.models.correction import Correction

def main():
    """检查作文状态"""
    # 创建应用上下文
    app = create_app()
    
    with app.app_context():
        # 获取所有作文
        essays = Essay.query.all()
        
        print("\n所有作文状态:")
        print("-" * 80)
        print(f"{'ID':^5} | {'标题':^30} | {'状态':^10} | {'创建时间':^20}")
        print("-" * 80)
        
        for essay in essays:
            # 获取对应的批改记录
            correction = Correction.query.filter_by(essay_id=essay.id).first()
            
            print(f"{essay.id:^5} | {essay.title[:28]:^30} | {essay.status:^10} | {essay.created_at.strftime('%Y-%m-%d %H:%M:%S'):^20}")
            
            if correction:
                print(f"     | 批改状态: {correction.status}")
                if correction.error_message:
                    print(f"     | 错误信息: {correction.error_message}")
            print("-" * 80)

if __name__ == "__main__":
    main() 