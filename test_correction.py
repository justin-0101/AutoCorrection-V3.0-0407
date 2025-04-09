#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改测试脚本
测试提交一篇作文进行批改，并直接调用批改方法
"""

from app import create_app
from app.core.correction.correction_service import CorrectionService
from app.core.services.init_services import ensure_services
from app.models.essay import Essay
from app.models.essay_status import EssayStatus
from app.extensions import db
import time
import json
import datetime

def test_direct_correction():
    """直接创建作文并调用批改方法，绕过用户限制检查"""
    # 创建Flask应用上下文
    app = create_app()
    
    with app.app_context():
        # 确保所有必要的服务已初始化
        print("初始化服务...")
        if not ensure_services():
            print("服务初始化失败")
            return
        
        print("服务初始化成功")
        
        # 创建批改服务
        correction_service = CorrectionService()
        
        # 测试作文内容
        title = "测试作文"
        content = """
        春天是一个充满生机和希望的季节。当冬天的寒冷逐渐褪去，万物开始苏醒。
        树木抽出新的嫩芽，花朵竞相绽放，鸟儿欢快地歌唱，整个世界仿佛披上了一层绿色的新装。
        
        春天给人们带来了无限的活力。人们脱下厚重的冬装，换上轻便的春装，走出家门，呼吸着新鲜的空气，
        感受着温暖的阳光。公园里，老人们散步聊天，孩子们奔跑嬉戏，青年人打球运动，
        到处洋溢着欢乐的气氛。
        
        春天也是播种的季节。农民们开始在田野里耕种，播下希望的种子。学生们也在这个季节里
        努力学习，为未来播下知识的种子。春天教会我们，只有辛勤耕耘，才能迎来丰收的喜悦。
        
        我爱春天，因为它象征着新的开始和无限的可能。在这个美丽的季节里，
        我们应该满怀希望，勇敢追逐自己的梦想，创造美好的未来。
        """
        
        # 直接创建作文记录，绕过用户限制检查
        print("直接创建作文记录...")
        essay = Essay(
            user_id=1,  # 假设用户ID为1
            title=title,
            content=content,
            source_type="test",
            status=EssayStatus.PENDING.value,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )
        db.session.add(essay)
        db.session.commit()
        
        essay_id = essay.id
        print(f"作文ID: {essay_id}")
        
        # 直接调用批改方法
        print("直接调用批改方法...")
        result = correction_service.perform_correction(essay_id)
        
        print(f"批改处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 再次获取结果确认
        correction_result = correction_service.get_correction_result(essay_id)
        print(f"批改最终结果: {json.dumps(correction_result, indent=2, ensure_ascii=False)}")
        
        # 获取作文状态
        essay = Essay.query.get(essay_id)
        print(f"作文状态: {essay.status}")
        
        return {
            "essay_id": essay_id,
            "result": result
        }

if __name__ == "__main__":
    result = test_direct_correction()
    print(f"测试完成: {json.dumps(result, indent=2, ensure_ascii=False) if result else '测试失败'}") 