#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试DeepSeek异步作文批改功能
"""

import os
import asyncio
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试作文内容
TEST_ESSAY = """
保护环境，从我做起

环境是我们赖以生存的家园，保护环境是每个人的责任。随着工业化进程的加快，环境问题日益突出，空气污染、水污染、土地荒漠化等问题严重威胁着人类的健康与生存。

我认为，保护环境应该从我做起，从小事做起。首先，我们可以减少使用一次性物品，比如自带购物袋、水杯等，减少白色污染。其次，我们应该养成垃圾分类的习惯，将可回收与不可回收的垃圾分开，促进资源的再利用。再次，节约用水用电，不仅能减少资源消耗，还能降低污染物的排放。

除了个人行动，我们还应该积极参与环保活动，比如植树造林、清洁海滩等，用实际行动保护我们的环境。同时，我们也可以通过学习环保知识，提高环保意识，并将这些知识传播给身边的人，让更多人加入到环保的行列中来。

环境保护不是一朝一夕的事情，需要我们持之以恒地努力。我相信，只要每个人都能从自身做起，从小事做起，我们的地球家园一定会变得更加美丽、更加适宜人类居住。
"""

async def test_async_correction():
    """测试异步批改功能"""
    try:
        print("\n" + "=" * 80)
        print(" 测试异步批改功能 ".center(80, "="))
        print("=" * 80 + "\n")
        
        # 导入批改服务
        from app.core.ai.ai_corrector import AICorrectionService
        
        # 创建批改服务实例
        corrector = AICorrectionService()
        
        # 开始时间
        start_time = datetime.now()
        print(f"[开始] 异步批改作文，长度: {len(TEST_ESSAY)}字，时间: {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # 异步调用批改方法
        result = await corrector.correct_essay_async(TEST_ESSAY)
        
        # 结束时间
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        print(f"[完成] 异步批改作文，耗时: {elapsed:.2f}秒，时间: {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # 输出结果
        if result and result.get("status") == "success":
            result_data = result.get("result", {})
            total_score = result_data.get("总得分", "未知")
            print(f"\n总得分: {total_score}")
            
            # 输出分项得分
            if "分项得分" in result_data:
                print("\n分项得分:")
                for item, score in result_data["分项得分"].items():
                    print(f"  {item}: {score}")
            
            # 输出总体评价
            if "总体评价" in result_data:
                print(f"\n总体评价: {result_data['总体评价'][:100]}...")
                
            # 输出错别字
            if "错别字" in result_data:
                print(f"\n错别字数量: {len(result_data['错别字'])}")
            
            # 判断是否为模拟结果
            if result_data.get("is_mock", False):
                print("\n注意: 这是一个模拟结果!")
                if "mock_reason" in result_data:
                    print(f"原因: {result_data['mock_reason']}")
                if "ai_error" in result_data:
                    print(f"AI错误: {result_data['ai_error']}")
        else:
            print(f"\n批改失败: {result.get('message', '未知错误')}")
            
        return result
        
    except Exception as e:
        print(f"\n异常: {str(e)}")
        logger.error(f"测试过程中出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

def test_sync_correction():
    """测试同步批改功能（用于比较）"""
    try:
        print("\n" + "=" * 80)
        print(" 测试同步批改功能 ".center(80, "="))
        print("=" * 80 + "\n")
        
        # 导入批改服务
        from app.core.ai.ai_corrector import AICorrectionService
        
        # 创建批改服务实例
        corrector = AICorrectionService()
        
        # 开始时间
        start_time = datetime.now()
        print(f"[开始] 同步批改作文，长度: {len(TEST_ESSAY)}字，时间: {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # 同步调用批改方法
        result = corrector.correct_essay(TEST_ESSAY)
        
        # 结束时间
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        print(f"[完成] 同步批改作文，耗时: {elapsed:.2f}秒，时间: {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # 输出简要结果
        if result and result.get("status") == "success":
            result_data = result.get("result", {})
            total_score = result_data.get("总得分", "未知")
            print(f"\n总得分: {total_score}")
            
            # 判断是否为模拟结果
            if result_data.get("is_mock", False):
                print("\n注意: 这是一个模拟结果!")
        else:
            print(f"\n批改失败: {result.get('message', '未知错误')}")
            
        return result
        
    except Exception as e:
        print(f"\n异常: {str(e)}")
        logger.error(f"测试过程中出错: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def main():
    """主函数"""
    # 先测试异步批改
    await test_async_correction()
    
    # 然后测试同步批改
    test_sync_correction()
    
    print("\n" + "=" * 80)
    print(" 测试完成 ".center(80, "="))
    print("=" * 80 + "\n")

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main()) 