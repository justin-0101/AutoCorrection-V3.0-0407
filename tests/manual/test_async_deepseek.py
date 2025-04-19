#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DeepSeek API异步调用测试脚本
"""

import os
import asyncio
import time
from datetime import datetime
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 从环境变量或配置文件加载
API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "=" * 50)
    if title:
        print(f" {title} ".center(50, "="))
    print("=" * 50 + "\n")

async def test_async_call():
    """测试异步调用DeepSeek API"""
    try:
        import openai
        
        print_separator("初始化OpenAI配置")
        print(f"使用API BASE URL: {BASE_URL}")
        print(f"使用模型: {MODEL}")
        
        # 设置OpenAI配置
        openai.api_key = API_KEY
        openai.api_base = BASE_URL
        
        # 测试消息
        messages = [
            {"role": "system", "content": "你是一位有用的助手。"},
            {"role": "user", "content": "你好，请给我一个简短的问候。"}
        ]
        
        # 请求参数
        params = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.1
        }
        
        print_separator("开始异步API调用")
        start_time = datetime.now()
        print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # 使用异步执行同步API调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: openai.ChatCompletion.create(**params)
        )
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"耗时: {elapsed:.2f}秒")
        
        # 输出响应
        message_content = response['choices'][0]['message']['content']
        print_separator("API响应")
        print(f"响应内容: {message_content}")
        
        return {"status": "success", "time": elapsed, "content": message_content}
    
    except Exception as e:
        print_separator("异常")
        print(f"发生错误: {str(e)}")
        logger.error(f"异步调用失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

def test_correction_service():
    """测试作文批改服务"""
    try:
        print_separator("测试作文批改服务")
        
        # 导入批改服务
        from app.core.ai.ai_corrector import AICorrectionService
        
        # 创建批改服务实例
        print("创建AICorrectionService实例...")
        corrector = AICorrectionService()
        
        # 测试作文内容
        test_content = """
        保护环境，从我做起
        
        环境是我们赖以生存的家园，保护环境是每个人的责任。随着工业化进程的加快，环境问题日益突出，空气污染、水污染、土地荒漠化等问题严重威胁着人类的健康与生存。
        
        我认为，保护环境应该从我做起，从小事做起。首先，我们可以减少使用一次性物品，比如自带购物袋、水杯等，减少白色污染。其次，我们应该养成垃圾分类的习惯，将可回收与不可回收的垃圾分开，促进资源的再利用。再次，节约用水用电，不仅能减少资源消耗，还能降低污染物的排放。
        
        除了个人行动，我们还应该积极参与环保活动，比如植树造林、清洁海滩等，用实际行动保护我们的环境。同时，我们也可以通过学习环保知识，提高环保意识，并将这些知识传播给身边的人，让更多人加入到环保的行列中来。
        
        环境保护不是一朝一夕的事情，需要我们持之以恒地努力。我相信，只要每个人都能从自身做起，从小事做起，我们的地球家园一定会变得更加美丽、更加适宜人类居住。
        """
        
        # 调用批改方法
        print(f"开始批改作文，内容长度: {len(test_content)}字")
        start_time = time.time()
        
        result = corrector.correct_essay(test_content)
        
        elapsed = time.time() - start_time
        print(f"批改完成，耗时: {elapsed:.2f}秒")
        
        # 输出结果
        print_separator("批改结果")
        if result.get("status") == "success":
            correction_result = result.get("result", {})
            print(f"总得分: {correction_result.get('总得分', '未知')}")
            print(f"总体评价: {correction_result.get('总体评价', '未提供')}")
        else:
            print(f"批改失败: {result.get('message', '未知错误')}")
        
        return result
    
    except Exception as e:
        print_separator("异常")
        print(f"批改服务测试失败: {str(e)}")
        logger.error(f"批改服务测试失败: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print_separator("DeepSeek API异步调用测试")
    
    # 测试异步API调用
    try:
        asyncio.run(test_async_call())
    except Exception as e:
        print(f"异步测试运行失败: {str(e)}")
    
    # 测试作文批改服务
    try:
        test_correction_service()
    except Exception as e:
        print(f"批改服务测试运行失败: {str(e)}")
    
    print_separator("测试完成") 