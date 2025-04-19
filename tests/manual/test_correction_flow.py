#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改流程测试脚本
测试整个作文提交和批改流程
"""

import os
import sys
import logging
import time
import argparse
import uuid
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_correction_flow.log')
    ]
)

logger = logging.getLogger(__name__)

def create_app_context():
    """创建应用上下文"""
    try:
        from app import create_app
        app = create_app()
        return app.app_context()
    except ImportError as e:
        logger.error(f"导入应用失败: {str(e)}")
        sys.exit(1)

def test_submit_essay(content_length=500, timeout=300):
    """
    测试提交作文并等待批改完成
    
    Args:
        content_length: 作文内容长度
        timeout: 超时时间（秒）
        
    Returns:
        dict: 测试结果
    """
    try:
        # 导入必要的模型和服务
        from app.models.essay import Essay, EssayStatus
        from app.models.correction import Correction, CorrectionStatus
        from app.core.correction.correction_service import CorrectionService
        from app.extensions import db
        
        # 实例化批改服务
        correction_service = CorrectionService()
        
        # 生成测试内容
        title = f"测试作文-{uuid.uuid4().hex[:8]}"
        
        # 生成随机作文内容
        content = generate_test_content(content_length)
        logger.info(f"生成测试作文: 《{title}》, 长度: {len(content)}字符")
        
        # 记录开始时间
        start_time = time.time()
        
        # 提交作文
        user_id = 1  # 默认使用ID为1的用户
        result = correction_service.submit_essay(user_id, title, content, grade="junior")
        logger.info(f"提交作文结果: {result}")
        
        if result.get('status') != 'success':
            logger.error(f"提交作文失败: {result.get('message')}")
            return {
                'success': False,
                'stage': 'submit',
                'message': result.get('message'),
                'result': result
            }
        
        # 获取作文ID
        essay_id = result.get('essay_id')
        if not essay_id:
            logger.error("提交作文成功但未返回作文ID")
            return {
                'success': False,
                'stage': 'submit',
                'message': '未获取到作文ID',
                'result': result
            }
        
        logger.info(f"成功提交作文，ID: {essay_id}，开始监控批改进度")
        
        # 等待批改完成
        elapsed = 0
        poll_interval = 5  # 每5秒查询一次状态
        completed = False
        
        while elapsed < timeout:
            # 查询作文状态
            essay = db.session.get(Essay, essay_id)
            if not essay:
                logger.error(f"无法找到作文，ID: {essay_id}")
                return {
                    'success': False,
                    'stage': 'monitor',
                    'message': f'无法找到作文，ID: {essay_id}',
                    'essay_id': essay_id,
                    'elapsed': elapsed
                }
            
            status = essay.status
            logger.info(f"作文状态: {status}，已耗时: {elapsed}秒")
            
            # 检查是否完成或失败
            if status == EssayStatus.COMPLETED.value:
                logger.info(f"作文批改已完成，ID: {essay_id}，总耗时: {elapsed}秒")
                completed = True
                break
            elif status == EssayStatus.FAILED.value:
                logger.error(f"作文批改失败，ID: {essay_id}，总耗时: {elapsed}秒")
                # 查询详细错误信息
                correction = db.session.query(Correction).filter_by(essay_id=essay_id).first()
                error_message = correction.error_message if correction else "未知错误"
                
                return {
                    'success': False,
                    'stage': 'correction',
                    'message': f'批改失败: {error_message}',
                    'essay_id': essay_id,
                    'elapsed': elapsed
                }
            
            # 等待一段时间后继续查询
            time.sleep(poll_interval)
            elapsed = int(time.time() - start_time)
        
        # 检查是否超时
        if not completed:
            logger.error(f"作文批改超时，ID: {essay_id}，已等待: {elapsed}秒")
            return {
                'success': False,
                'stage': 'timeout',
                'message': f'批改超时，已等待: {elapsed}秒',
                'essay_id': essay_id,
                'elapsed': elapsed
            }
        
        # 批改成功，获取结果
        correction_result = correction_service.get_correction_result(essay_id)
        logger.info(f"获取批改结果: {correction_result.get('status')}")
        
        # 返回成功结果
        return {
            'success': True,
            'stage': 'completed',
            'message': '批改完成',
            'essay_id': essay_id,
            'elapsed': elapsed,
            'correction': correction_result
        }
        
    except Exception as e:
        import traceback
        logger.error(f"测试过程中发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'stage': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }

def generate_test_content(length=500):
    """
    生成测试用的作文内容
    
    Args:
        length: 大约的字符长度
        
    Returns:
        str: 生成的作文内容
    """
    # 作文段落模板
    paragraphs = [
        "春天来了，万物复苏，大地一片生机勃勃的景象。小草从土里钻出来，嫩嫩的，绿绿的。柳树抽出了新的枝条，风一吹，柳条随风摆动，好像在跳舞。",
        "夏天到了，骄阳似火，小河里的水清澈见底，我和小伙伴们跳进河里，溅起一朵朵水花，我们嬉戏玩耍，欢声笑语回荡在水面上。",
        "秋天是收获的季节，果园里的苹果红了，梨子黄了，葡萄紫了。农民伯伯的脸上洋溢着丰收的喜悦，他们辛勤劳动的汗水没有白流。",
        "冬天是银装素裹的世界，一场大雪过后，整个世界变成了白色。孩子们堆雪人，打雪仗，玩得不亦乐乎。",
        "我的家乡有一条美丽的河流，河水清澈见底，小鱼在水中自由自在地游来游去。河边的柳树倒映在水中，构成了一幅美丽的画卷。",
        "我们班上有一个图书角，里面有许多有趣的书籍。每到课间休息，同学们都会到图书角看书，教室里安静极了，只有翻书的声音。",
        "保护环境人人有责，我们要从自己做起，不乱扔垃圾，不浪费水资源，爱护花草树木，让我们的地球妈妈更加美丽。",
        "互联网的发展给我们的生活带来了很多便利，我们可以通过网络学习知识，和远方的朋友聊天，了解世界各地的新闻。",
        "中华文化源远流长，五千年的历史长河孕育了丰富多彩的传统文化。我们应该传承和发扬中华民族的优秀传统文化。",
        "奶奶的厨艺非常好，每次回奶奶家，她都会做很多好吃的菜。香喷喷的饭菜不仅满足了我的胃口，更让我感受到了浓浓的亲情。"
    ]
    
    # 根据需要的长度选择段落
    result = []
    current_length = 0
    
    while current_length < length:
        for para in paragraphs:
            if current_length >= length:
                break
            result.append(para)
            current_length += len(para)
    
    return "".join(result)[:length]

def analyze_test_results(results):
    """
    分析测试结果
    
    Args:
        results: 测试结果列表
        
    Returns:
        dict: 分析结果
    """
    total = len(results)
    success_count = sum(1 for r in results if r.get('success'))
    failed_count = total - success_count
    success_rate = success_count / total if total > 0 else 0
    
    # 计算平均耗时
    elapsed_times = [r.get('elapsed') for r in results if r.get('success') and r.get('elapsed')]
    avg_time = sum(elapsed_times) / len(elapsed_times) if elapsed_times else 0
    
    # 统计失败原因
    failure_reasons = {}
    for r in results:
        if not r.get('success'):
            stage = r.get('stage', 'unknown')
            failure_reasons[stage] = failure_reasons.get(stage, 0) + 1
    
    return {
        'total_tests': total,
        'success_count': success_count,
        'failed_count': failed_count,
        'success_rate': success_rate,
        'avg_processing_time': avg_time,
        'failure_reasons': failure_reasons
    }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='作文批改流程测试工具')
    parser.add_argument('--count', type=int, default=1, help='测试次数，默认1次')
    parser.add_argument('--length', type=int, default=500, help='作文长度，默认500字符')
    parser.add_argument('--timeout', type=int, default=300, help='超时时间（秒），默认300秒')
    
    args = parser.parse_args()
    
    logger.info(f"作文批改流程测试启动，测试次数: {args.count}，作文长度: {args.length}字符，超时: {args.timeout}秒")
    
    # 创建应用上下文
    with create_app_context():
        results = []
        
        for i in range(args.count):
            logger.info(f"开始第 {i+1}/{args.count} 次测试")
            result = test_submit_essay(args.length, args.timeout)
            results.append(result)
            
            if result.get('success'):
                logger.info(f"测试 #{i+1} 成功完成, 耗时: {result.get('elapsed')}秒")
            else:
                logger.error(f"测试 #{i+1} 失败: {result.get('message')}")
            
            # 如果不是最后一次测试，等待一段时间再进行下一次
            if i < args.count - 1:
                time.sleep(5)
        
        # 分析结果
        analysis = analyze_test_results(results)
        logger.info(f"测试完成，总结:")
        logger.info(f"总测试次数: {analysis['total_tests']}")
        logger.info(f"成功: {analysis['success_count']}，失败: {analysis['failed_count']}")
        logger.info(f"成功率: {analysis['success_rate'] * 100:.2f}%")
        logger.info(f"平均处理时间: {analysis['avg_processing_time']:.2f}秒")
        
        if analysis['failure_reasons']:
            logger.info("失败原因统计:")
            for stage, count in analysis['failure_reasons'].items():
                logger.info(f"- {stage}: {count}次")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        logger.error(f"执行测试脚本时出错: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1) 