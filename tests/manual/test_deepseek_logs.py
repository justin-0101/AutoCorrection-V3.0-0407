#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试Deepseek批改日志输出
直接调用AI批改功能，观察日志输出
"""

import os
import sys
import time
from datetime import datetime

# 设置环境变量
os.environ["FLASK_APP"] = "wsgi.py"
os.environ["FLASK_ENV"] = "development"

# 确保能够导入应用模块
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 导入AI批改相关模块
from app.core.ai.ai_corrector import AICorrectionService
from app.core.ai.deepseek_client import DeepseekClient

def test_direct_correction():
    """直接测试AI批改功能"""
    print("-" * 50)
    print(f"开始测试Deepseek批改功能，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # 创建AI批改服务实例
    corrector = AICorrectionService()
    
    # 测试用作文内容
    test_content = """
    我的环保梦想
    
    在这个日新月异的时代，环境问题日益突出，保护环境已经成为全人类的共同责任。作为新时代的青少年，我有一个环保梦想，希望通过自己的努力，为保护地球环境贡献一份力量。
    
    我梦想着有一天，天空会更蓝，云朵会更白，河流会更清，树木会更绿。为了这个梦想，我首先要从身边的小事做起。我会随手关灯，节约用水，减少使用一次性物品，积极参与垃圾分类。这些看似微不足道的行动，如果人人都能坚持，就会汇聚成保护环境的巨大力量。
    
    其次，我会不断学习环保知识，了解更多保护环境的方法。通过阅读环保书籍，参加环保讲座，观看环保纪录片，我可以增长环保知识，提高环保意识。同时，我也会将这些知识分享给身边的家人和朋友，影响更多的人加入到环保行动中来。
    
    此外，我还会积极参与环保活动。比如参加社区组织的植树活动，为城市增添绿色；参与海滩清洁行动，保护海洋生态；参加环保宣传活动，提高公众的环保意识。通过这些实际行动，我不仅能够直接为环境保护做出贡献，还能够影响更多的人关注环境问题。
    
    我相信，只要我们携起手来，共同努力，就一定能够创造一个更加美好、更加环保的世界。环保不是一个人的责任，而是所有人的责任。让我们一起行动起来，保护我们共同的家园——地球！
    
    我的环保梦想虽然简单，但我会用实际行动去实现它。我相信，星星之火可以燎原，只要每个人都献出一点爱，世界将变成美好的人间。
    """
    
    # 直接调用批改功能
    print("开始调用批改功能...")
    start_time = datetime.now()
    
    # 执行批改
    result = corrector.correct_essay(test_content)
    
    # 计算总耗时
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    # 输出结果概要
    print("-" * 50)
    print(f"批改完成，总耗时: {elapsed:.2f}秒")
    
    if result["status"] == "success":
        total_score = result.get("result", {}).get("total_score", "未知")
        print(f"批改结果: 总分 = {total_score}")
        
        # 输出详细结果
        print("\n详细结果:")
        print("-" * 50)
        for key, value in result.get("result", {}).items():
            if isinstance(value, dict):
                print(f"{key}:")
                for sub_key, sub_value in value.items():
                    print(f"  - {sub_key}: {sub_value}")
            else:
                print(f"{key}: {value}")
    else:
        print(f"批改失败: {result.get('message', '未知错误')}")
    
    print("-" * 50)

if __name__ == "__main__":
    test_direct_correction() 