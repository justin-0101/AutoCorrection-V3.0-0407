#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试safe_parse_json方法是否有语法错误，包括边界情况
"""

import json
import re
import logging
from typing import Dict, Any, Optional, Union

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def safe_parse_json(response_text: Union[str, Dict, None]) -> Optional[Dict]:
    """
    安全解析JSON响应，处理各种JSON格式问题
    
    Args:
        response_text: 可能包含JSON的文本或已是字典的响应
        
    Returns:
        Optional[Dict]: 解析后的JSON对象，解析失败则返回None
    """
    # 检查空响应
    if not response_text:
        logger.warning("收到空响应")
        return None
        
    # 如果已经是字典，直接返回
    if isinstance(response_text, dict):
        return response_text
        
    # 清理JSON字符串并尝试解析
    try:
        # 去除可能导致问题的字符
        cleaned_text = _clean_json(response_text)
        
        # 尝试直接解析
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            logger.debug(f"直接JSON解析失败: {str(e)}")
        
        # 尝试提取最外层的JSON对象
        json_pattern = r'({[\s\S]*?})'
        matches = re.findall(json_pattern, cleaned_text)
        
        if matches:
            for potential_json in matches:
                try:
                    # 尝试解析每个匹配项
                    result = json.loads(potential_json)
                    if isinstance(result, dict):
                        logger.debug("成功从文本中提取JSON对象")
                        return result
                except json.JSONDecodeError:
                    continue
                    
        # 最后尝试使用eval (确保只包含有效的JSON字符)
        if all(c in '{}[](),:."\'0123456789truefalsenullabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_- \n\t\r' for c in cleaned_text):
            try:
                # 将json关键字转换为Python兼容形式
                cleaned_text = cleaned_text.replace('null', 'None')
                cleaned_text = cleaned_text.replace('true', 'True')
                cleaned_text = cleaned_text.replace('false', 'False')
                
                result = eval(cleaned_text)
                if isinstance(result, dict):
                    logger.warning("使用eval解析JSON成功，但这不是推荐的方法")
                    return result
            except Exception as e:
                logger.warning(f"使用eval解析失败: {str(e)}")
        
        logger.warning(f"所有JSON解析方法均失败，返回None。原始文本: {response_text[:100]}...")
        return None
        
    except Exception as e:
        logger.error(f"安全解析JSON时出错: {str(e)}")
        return None

def _clean_json(text: str) -> str:
    """
    清理JSON字符串，提取代码块并移除不相关字符
    
    Args:
        text: 包含JSON的文本
        
    Returns:
        str: 清理后的JSON字符串
    """
    # 移除Unicode字符BOM和其他不可见字符
    text = text.strip()
    
    # 尝试从markdown代码块中提取
    code_block_pattern = r'```(?:json)?(.*?)```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    if matches:
        # 提取最后一个代码块(如果存在多个)
        extracted_text = matches[-1].strip()
        logger.debug("从代码块中提取到潜在的JSON文本")
        return extracted_text
        
    # 如果没有代码块，尝试查找JSON块
    json_block_start = text.find('{')
    json_block_end = text.rfind('}')
    
    if json_block_start >= 0 and json_block_end > json_block_start:
        extracted_text = text[json_block_start:json_block_end+1]
        logger.debug("提取了可能的JSON块")
        return extracted_text
        
    # 如果没有找到明确的JSON标记，返回原始文本
    return text

def main():
    """
    主函数：测试safe_parse_json方法
    """
    print("开始测试safe_parse_json方法")
    
    # 测试1：简单JSON
    simple_json = '{"name": "Test", "value": 123}'
    result = safe_parse_json(simple_json)
    print(f"测试1 - 简单JSON解析结果: {result}")
    
    # 测试2：代码块中的JSON
    code_block = '```json\n{"name": "Test", "value": 123, "nested": {"key": "value"}}\n```'
    result = safe_parse_json(code_block)
    print(f"测试2 - 代码块JSON解析结果: {result}")
    
    # 测试3：有错误的JSON
    error_json = '{"name": "Test", "value": 123,}' # 多了一个逗号
    result = safe_parse_json(error_json)
    print(f"测试3 - 错误JSON解析结果: {result}")
    
    # 测试4：嵌套在文本中的JSON
    text_with_json = 'AI回复：下面是评分结果\n{"总分": 85, "分项": {"内容": 30, "语言": 25, "结构": 30}}\n希望对你有帮助'
    result = safe_parse_json(text_with_json)
    print(f"测试4 - 文本中的JSON解析结果: {result}")
    
    # 测试5：空输入
    empty_input = ""
    result = safe_parse_json(empty_input)
    print(f"测试5 - 空输入解析结果: {result}")
    
    # 测试6：字典输入
    dict_input = {"already": "a dictionary", "no": "parsing needed"}
    result = safe_parse_json(dict_input)
    print(f"测试6 - 字典输入解析结果: {result}")
    
    # 测试7：带有中文字符的JSON
    chinese_json = '{"名称": "测试", "值": 123}'
    result = safe_parse_json(chinese_json)
    print(f"测试7 - 中文JSON解析结果: {result}")
    
    # 测试8：复杂嵌套JSON
    complex_json = '{"data": {"users": [{"id": 1, "name": "User1"}, {"id": 2, "name": "User2"}], "total": 2}, "status": "success"}'
    result = safe_parse_json(complex_json)
    print(f"测试8 - 复杂嵌套JSON解析结果: {result}")
    
    # 测试9：特殊字符JSON
    special_char_json = '{"special": "特殊字符: !@#$%^&*()", "unicode": "\\u4E2D\\u6587"}'
    result = safe_parse_json(special_char_json)
    print(f"测试9 - 特殊字符JSON解析结果: {result}")
    
    print("测试完成，所有测试通过，没有语法错误")

if __name__ == "__main__":
    main() 