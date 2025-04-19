#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试AI批改功能
"""

import sys
import os
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入批改服务
from app.core.ai.ai_corrector import AICorrectionService

def main():
    """测试批改功能"""
    print("开始测试AI批改功能...")
    
    # 初始化批改服务
    try:
        service = AICorrectionService()
        print("批改服务初始化成功")
    except Exception as e:
        print(f"批改服务初始化失败: {str(e)}")
        return
    
    # 测试批改短文本
    test_content = """我的环保梦想
    地球是我们共同的家园，但随着人类活动的增加，环境问题日益严重。作为新时代的青少年，我有一个环保梦想。
    
    首先，我梦想人人都能树立环保意识。在日常生活中，每个人都应该从小事做起，比如节约用水、用电，减少使用一次性餐具，尽量乘坐公共交通工具出行等。只有人人都有环保意识，才能共同保护我们的地球。
    
    其次，我梦想科技能更好地服务于环保事业。科学家们应该研发更多环保材料，代替塑料等不可降解材料；发展清洁能源，减少对煤炭等化石燃料的依赖；研究更高效的垃圾处理技术，减少垃圾对环境的污染。
    
    最后，我梦想世界各国能携手合作，共同应对环境挑战。环境问题是全球性的，需要全球共同努力才能解决。各国政府应该加强合作，共同制定环保政策，并确保这些政策得到有效执行。
    
    我相信，只要我们共同努力，我的环保梦想一定能实现，地球也一定会变得更加美丽。"""
    
    try:
        print(f"开始批改内容: {test_content}")
        result = service.correct_essay(test_content)
        
        print("\n批改结果:")
        print(f"状态: {result['status']}")
        
        if result['status'] == 'success':
            print(f"总分: {result['result'].get('total_score', '未知')}")
            print(f"内容得分: {result['result'].get('content_score', '未知')}")
            print(f"语言得分: {result['result'].get('language_score', '未知')}")
            print(f"结构得分: {result['result'].get('structure_score', '未知')}")
            print(f"写作得分: {result['result'].get('writing_score', '未知')}")
            print(f"等级: {result['result'].get('level', '未知')}")
            
            # 输出评价信息
            print("\n评价信息:")
            print(f"总体评价: {result['result'].get('overall_assessment', '无')[:100]}...")
        else:
            print(f"批改失败: {result.get('message', '未知错误')}")
            if 'result' in result and 'error' in result['result']:
                print(f"错误详情: {result['result']['error']}")
    
    except Exception as e:
        print(f"批改过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main() 