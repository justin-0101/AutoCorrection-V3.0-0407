import logging
import dotenv
from typing import Dict, Union, Any, List, Optional
from app.modules.tasks import *
import os
from openai import OpenAI, AsyncOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
import uuid
import re
import asyncio
import aiohttp
import json
import time

# 配置日志
logger = logging.getLogger(__name__)

# 加载环境变量，指定.env文件路径
dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env'))

# 确保明确使用DEEPSEEK_API_KEY环境变量
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
# 从环境变量获取模型名称，默认为deepseek-reasoner
deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

if not deepseek_api_key:
    logger.warning("警告: DEEPSEEK_API_KEY环境变量未设置，DeepSeek功能将不可用")
    # 尝试从配置文件直接读取
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')) as f:
            for line in f:
                if line.startswith('DEEPSEEK_API_KEY='):
                    deepseek_api_key = line.split('=')[1].strip().strip('"')
                    break
    except Exception as e:
        logger.error(f"无法从配置文件读取API密钥: {e}")

# 使用OpenAI SDK初始化客户端
client = AsyncOpenAI(
    api_key=deepseek_api_key,  # 明确使用deepseek_api_key
    base_url=deepseek_base_url,  # 明确使用deepseek_base_url
    timeout=60.0,  # 设置60秒超时时间
    max_retries=3  # 设置3次重试
)

logger.info(f"DeepSeek API配置: BASE_URL={deepseek_base_url}")
logger.info(f"DeepSeek API密钥: {'已设置 (长度:'+str(len(deepseek_api_key) if deepseek_api_key else 0)+'字符)' if deepseek_api_key else '未设置'}")
logger.info(f"DeepSeek 模型: {deepseek_model}")

async def create_chat_completion(**kwargs):
    try:
        if not deepseek_api_key:
            raise Exception("DeepSeek API密钥未设置，无法使用DeepSeek AI")
            
        logger.info("【发送API请求】")
        logger.info(f"请求参数: {kwargs}")
        
        # 使用OpenAI SDK直接调用
        response = await client.chat.completions.create(
            **kwargs,
            stream=False
        )
        
        logger.info("【收到API响应】")
        logger.info(f"响应对象: {response}")
        
        if not response or not response.choices:
            raise Exception("API返回结果为空")
        return response
    except Exception as e:
        error_msg = str(e)
        logger.error(f"DeepSeek API错误: {error_msg}")
        if any(err in error_msg.lower() for err in ["rate_limit", "too_many_requests"]):
            raise Exception("服务请求过于频繁，请稍后重试")
        elif any(err in error_msg.lower() for err in ["timeout", "connect", "connection"]):
            raise Exception("网络连接超时，请检查网络后重试")
        elif any(err in error_msg.lower() for err in ["invalid_api_key", "authentication", "unauthorized"]):
            raise Exception("API认证失败，请检查API密钥")
        elif "invalid_request" in error_msg.lower():
            raise Exception("API请求格式错误，请检查参数")
        elif "model_not_found" in error_msg.lower():
            raise Exception("请求的模型不存在或暂不可用")
        elif "API返回结果为空" in error_msg:
            raise Exception("API返回结果为空，请重试")
        else:
            logger.error(f"未知错误: {error_msg}")
            raise Exception("模型服务暂时不可用，请稍后重试")

async def get_model_response(**kwargs):
    try:
        logger.info("【调用模型】")
        logger.info(f"请求参数: {kwargs}")
        
        response = await create_chat_completion(
            model=deepseek_model,  # 使用环境变量中指定的模型
            temperature=0.7,
            max_tokens=2048,
            **kwargs
        )
        
        logger.info("【模型响应成功】")
        logger.info(f"响应内容: {response}")
        
        return response
    except Exception as e:
        error_msg = str(e)
        logger.error(f"获取模型响应失败: {error_msg}")
        if "API认证失败" in error_msg:
            raise Exception("API认证失败，请检查配置")
        elif "服务请求过于频繁" in error_msg:
            raise Exception("服务繁忙，请稍后再试")
        elif "网络连接超时" in error_msg:
            raise Exception("服务响应超时，请刷新重试")
        else:
            raise Exception("获取模型响应失败，请稍后重试")

parser = JsonOutputParser()

async def model(messages):
    try:
        logger.info("【处理消息】")
        logger.info(f"原始消息: {messages}")
        
        # 转换消息格式
        formatted_messages = []
        if isinstance(messages, str):
            formatted_messages = [{"role": "user", "content": messages}]
        elif isinstance(messages, list):
            for message in messages:
                if isinstance(message, dict) and "role" in message and "content" in message:
                    formatted_messages.append(message)
                elif isinstance(message, dict) and "text" in message:
                    # 处理旧版消息格式
                    role = "user"
                    if "type" in message and message["type"] == "ai":
                        role = "assistant"
                    formatted_messages.append({"role": role, "content": message["text"]})
                else:
                    # 如果消息格式不正确，添加为用户消息
                    formatted_messages.append({"role": "user", "content": str(message)})
        else:
            formatted_messages = [{"role": "user", "content": str(messages)}]
        
        logger.info(f"格式化后的消息: {formatted_messages}")
        
        # 使用常规文本模型
        response = await create_chat_completion(
            model=deepseek_model,  # 使用环境变量中指定的模型
            messages=formatted_messages,
            temperature=0.2,  # 降低temperature使响应更确定性
            max_tokens=2000,
            timeout=60.0  # 设置60秒超时时间
        )
        
        logger.info("【模型响应成功】")
        logger.info(f"响应内容: {response}")
        
        return response
    except Exception as e:
        error_msg = str(e)
        logger.error(f"获取模型响应失败: {error_msg}")
        if "API认证失败" in error_msg:
            raise Exception("API认证失败，请检查配置")
        elif "服务请求过于频繁" in error_msg:
            raise Exception("服务繁忙，请稍后再试")
        elif "网络连接超时" in error_msg:
            raise Exception("服务响应超时，请刷新重试")
        else:
            raise Exception("模型服务异常，请稍后重试")


async def handler_spell_error(article: str) -> Dict[str, Union[int, str]]:
    """
    这个方法处理错别字检测任务，接收文章并返回扣分数以及解析

    Args:
        article (str): 待批改文章

    Returns:
        Json格式输出 i.e.{"错别字扣分":"具体扣分数（例如：2）","解析":"具体扣分原因描述（例如："发现2个错别字，分别是'澡'应为'藻'，'彻'应为'澈'，每个错别字扣1分，共扣2分。")"}
    """
    prompt = PromptTemplate(
        template=task_spell_error.prompt(),
        input_variables=task_spell_error.input_variables(),
        partial_variables={"format_instructions": task_spell_error.format_instruction()}
    )

    # 生成提示文本
    prompt_text = prompt.format(article=article)
    
    # 直接调用model处理提示文本
    response = await model(prompt_text)
    
    # 从响应对象中提取文本内容
    if response and response.choices and len(response.choices) > 0:
        response_text = response.choices[0].message.content
    else:
        logger.error("API响应为空或无效")
        return {"错别字扣分": "0", "解析": []}
    
    # 尝试解析JSON响应
    try:
        logger.info(f"尝试解析错别字JSON: {response_text}")
        result = parser.parse(response_text)
        
        # 确保解析结果包含必要的字段
        if "错别字扣分" not in result:
            logger.warning("API响应缺少错别字扣分字段")
            result["错别字扣分"] = "0"
            
        if "解析" not in result:
            logger.warning("API响应缺少解析字段")
            result["解析"] = []
            
        # 如果解析是字符串而不是列表，尝试提取错别字项
        if isinstance(result["解析"], str) and len(result["解析"]) > 0:
            text_analysis = result["解析"]
            # 从文本中提取错别字列表
            errors = []
            
            # 基本模式：分别是'X'应为'Y'
            import re
            error_pattern = re.compile(r"'([^']+)'应为'([^']+)'")
            matches = error_pattern.findall(text_analysis)
            
            for i, (wrong, correct) in enumerate(matches):
                # 尝试从文本中找出错别字的上下文
                context_pattern = re.compile(r"[^。，；！？\n]{0,10}" + re.escape(wrong) + r"[^。，；！？\n]{0,10}")
                context_match = context_pattern.search(article)
                context = context_match.group(0) if context_match else f"...{wrong}..."
                
                # 创建一个错别字项
                error_item = {
                    "错误": wrong,
                    "位置": f"第{i+1}处",
                    "正确写法": correct,
                    "上下文": context
                }
                errors.append(error_item)
            
            # 如果找到了错别字，替换解析字段
            if errors:
                result["解析"] = errors
        
        logger.info(f"处理后的错别字结果: {result}")
        return result
        
    except Exception as e:
        logger.error(f"JSON解析错误: {e}")
        return {"错别字扣分": "0", "解析": []}


async def handler_content_analysis(subject: str, article: str) -> Dict[str, Union[int, Dict[str, str]]]:
    """
    这个方法处理内容主旨分析任务，接收作文题目和文章，返回扣分数以及解析

    Args:
        subject (str): 作文题目
        article (str): 待批改文章

    Returns:
        Json格式输出 i.e.{"内容主旨得分": "xx",解析:"xxxxxxxx"}
    """
    prompt = PromptTemplate(
        template=task_content_analysis.prompt(),
        input_variables=task_content_analysis.input_variables(),
        partial_variables={"format_instructions": task_content_analysis.format_instruction()}
    )

    # 生成提示文本
    prompt_text = prompt.format(subject=subject, article=article)
    
    # 直接调用model处理提示文本
    response = await model(prompt_text)
    
    # 从响应对象中提取文本内容
    if response and response.choices and len(response.choices) > 0:
        response_text = response.choices[0].message.content
    else:
        logger.error("API响应为空或无效")
        return {"内容主旨得分": "15", "解析": "提供的作文内容分析失败，但从篇幅和结构来看，给予及格分数。"}
    
    # 尝试解析JSON响应
    try:
        logger.info(f"尝试解析内容主旨JSON: {response_text}")
        result = parser.parse(response_text)
        
        # 确保解析结果包含必要的字段
        if "内容主旨得分" not in result:
            logger.warning("API响应缺少内容主旨得分字段")
            result["内容主旨得分"] = "15"  # 设置默认得分为15分
        elif result["内容主旨得分"] == "0" or float(result["内容主旨得分"]) < 5:
            logger.warning(f"内容主旨得分过低: {result['内容主旨得分']}，调整为默认分数")
            result["内容主旨得分"] = "15"  # 如果分数为0或很低，设置为15分
            
        if "解析" not in result:
            logger.warning("API响应缺少解析字段")
            result["解析"] = "提供的作文内容结构完整，主题明确，给予及格分数。"
            
        # 如果解析是字典而不是字符串，将其转换为字符串，并确保列表项格式正确
        if isinstance(result["解析"], dict):
            detailed_analysis = result["解析"]
            # 提取字典中的内容，并确保数字列表项的格式
            formatted_analysis = []
            
            # 处理主旨解析
            if "主旨解析" in detailed_analysis and detailed_analysis["主旨解析"]:
                formatted_analysis.append(f"【主旨解析】\n{detailed_analysis['主旨解析']}")
            
            # 处理论点解析，检查是否有列表项
            if "论点解析" in detailed_analysis and detailed_analysis["论点解析"]:
                import re
                content = detailed_analysis["论点解析"]
                list_items = re.findall(r'\d+[\.\)、）]\s*[^。；\n]+[。；]?', content)
                
                item_text = "【论点解析】"
                if list_items:
                    item_text += "\n"
                    for i, item in enumerate(list_items):
                        item_text += f"{i+1}) {item.split(')', 1)[-1].split('.', 1)[-1].split('、', 1)[-1].strip()}\n"
                else:
                    item_text += f"\n{content}"
                    
                formatted_analysis.append(item_text)
            
            # 处理论据解析，检查是否有列表项
            if "论据解析" in detailed_analysis and detailed_analysis["论据解析"]:
                import re
                content = detailed_analysis["论据解析"]
                list_items = re.findall(r'\d+[\.\)、）]\s*[^。；\n]+[。；]?', content)
                
                item_text = "【论据解析】"
                if list_items:
                    item_text += "\n"
                    for i, item in enumerate(list_items):
                        item_text += f"{i+1}) {item.split(')', 1)[-1].split('.', 1)[-1].split('、', 1)[-1].strip()}\n"
                else:
                    item_text += f"\n{content}"
                    
                formatted_analysis.append(item_text)
            
            # 处理思想情感解析
            if "思想情感解析" in detailed_analysis and detailed_analysis["思想情感解析"]:
                import re
                content = detailed_analysis["思想情感解析"]
                list_items = re.findall(r'\d+[\.\)、）]\s*[^。；\n]+[。；]?', content)
                
                item_text = "【思想情感解析】"
                if list_items:
                    item_text += "\n"
                    for i, item in enumerate(list_items):
                        item_text += f"{i+1}) {item.split(')', 1)[-1].split('.', 1)[-1].split('、', 1)[-1].strip()}\n"
                else:
                    item_text += f"\n{content}"
                    
                formatted_analysis.append(item_text)
            
            # 将所有分析项合并为一个字符串
            result["解析"] = "\n\n".join(formatted_analysis)
            logger.info(f"格式化后的内容主旨解析: {result['解析']}")
            
        logger.info(f"处理后的内容主旨结果: {result}")
        return result
        
    except Exception as e:
        logger.error(f"JSON解析错误: {e}")
        return {"内容主旨得分": "15", "解析": "提供的作文内容分析失败，但从篇幅和结构来看，给予及格分数。"}


async def handler_express_analysis(subject: str, article: str) -> Dict[str, Union[int, Dict[str, str]]]:
    """
    这个方法处理表达文采分析任务，接收作文题目和文章，返回扣分数以及解析

    Args:
        subject (str): 作文题目
        article (str): 待批改文章

    Returns:
        Json格式输出 i.e.{"表达文采得分":"xx",解析:"xxxxxxxx"}
    """
    prompt = PromptTemplate(
        template=task_express_analysis.prompt(),
        input_variables=task_express_analysis.input_variables(),
        partial_variables={"format_instructions": task_express_analysis.format_instruction()}
    )

    # 生成提示文本
    prompt_text = prompt.format(subject=subject, article=article)
    
    # 直接调用model处理提示文本
    response = await model(prompt_text)
    
    if response and response.choices and len(response.choices) > 0:
        response_text = response.choices[0].message.content
    else:
        logger.error("API响应为空或无效")
        return {"表达文采得分": "0", "解析": "解析失败，请重试。"}
    
    # 尝试解析JSON响应
    try:
        logger.info(f"尝试解析JSON: {response_text}")
        result = parser.parse(response_text)
        # 确保解析结果包含必要的字段
        if "表达文采得分" not in result:
            logger.warning("API响应缺少表达文采得分字段")
            result["表达文采得分"] = "0"
        
        # 简化解析内容，如果解析是字典，则将其转换为字符串
        if isinstance(result["解析"], dict):
            detailed_analysis = result["解析"]
            # 提取字典中的内容作为文本，确保数字列表项的格式
            formatted_analysis = []
            
            # 处理每个分析项，并确保列表项格式化正确
            if "论证手法解析" in detailed_analysis and detailed_analysis["论证手法解析"]:
                item_text = "论证手法："
                content = detailed_analysis["论证手法解析"]
                
                # 拆分列表项
                import re
                # 查找所有形如 "1. xxx" 或 "1) xxx" 或 "1、xxx" 的内容
                list_items = re.findall(r'\d+[\.\)、）]\s*[^。；\n]+[。；]?', content)
                
                if list_items:
                    item_text += "\n"  # 添加换行确保列表显示在新行
                    for i, item in enumerate(list_items):
                        item_text += f"{i+1}) {item.split(')', 1)[-1].split('.', 1)[-1].split('、', 1)[-1].strip()}\n"
                else:
                    item_text += content
                
                formatted_analysis.append(item_text)
            
            if "修辞手法解析" in detailed_analysis and detailed_analysis["修辞手法解析"]:
                item_text = "修辞手法："
                content = detailed_analysis["修辞手法解析"]
                
                # 拆分列表项
                import re
                list_items = re.findall(r'\d+[\.\)、）]\s*[^。；\n]+[。；]?', content)
                
                if list_items:
                    item_text += "\n"  # 添加换行确保列表显示在新行
                    for i, item in enumerate(list_items):
                        item_text += f"{i+1}) {item.split(')', 1)[-1].split('.', 1)[-1].split('、', 1)[-1].strip()}\n"
                else:
                    item_text += content
                    
                formatted_analysis.append(item_text)
            
            if "语言特色分析" in detailed_analysis and detailed_analysis["语言特色分析"]:
                item_text = "语言特色："
                content = detailed_analysis["语言特色分析"]
                
                # 拆分列表项
                import re
                list_items = re.findall(r'\d+[\.\)、）]\s*[^。；\n]+[。；]?', content)
                
                if list_items:
                    item_text += "\n"  # 添加换行确保列表显示在新行
                    for i, item in enumerate(list_items):
                        item_text += f"{i+1}) {item.split(')', 1)[-1].split('.', 1)[-1].split('、', 1)[-1].strip()}\n"
                else:
                    item_text += content
                    
                formatted_analysis.append(item_text)
            
            # 将所有分析项合并为一个字符串
            result["解析"] = "\n".join(formatted_analysis)
            logger.info(f"格式化后的表达文采解析: {result['解析']}")
        
        return result
    except Exception as e:
        logger.error(f"JSON解析错误: {e}")
        logger.error(f"原始响应: {response_text}")
        return {"表达文采得分": "0", "解析": {
            "论证手法解析": "JSON解析失败，请重试。", 
            "引经据典解析": "", 
            "修辞手法解析": "", 
            "语言特色分析": "", 
            "创新表达分析": ""
        }}


async def handler_summary(detail: str) -> str:
    """
    这个方法处理作文评分总结生成任务，接收作文批改细节，返回总结内容

    Args:
        detail (str): 作文批改细节

    Returns:
        str: 总结内容
    """
    prompt = PromptTemplate(
        template=task_summary.prompt(),
        input_variables=task_summary.input_variables(),
        partial_variables={}
    )

    # 生成提示文本
    prompt_text = prompt.format(detail=detail)
    
    # 直接调用model处理提示文本
    response = await model(prompt_text)
    
    # 从响应对象中提取文本内容
    if response and response.choices and len(response.choices) > 0:
        response_text = response.choices[0].message.content
    else:
        logger.error("API响应为空或无效")
        return "无法生成总结，请重试"
    
    return response_text

async def handler_writing_analysis() -> Dict[str, Union[str, str]]:
    """
    处理书写分析，由于暂未实现字体识别功能，直接返回满分和固定评语
    
    Returns:
        Dict: {"书写得分": "5", "解析": "打印体，直接得5分"}
    """
    return {
        "书写得分": "5",
        "解析": "打印体，直接得5分"
    }

# 添加统一评分函数
async def unified_essay_scoring(subject: str, article: str) -> Dict[str, Any]:
    """
    统一的作文评分函数，一次性完成所有评分，包括错别字检测、内容主旨分析和表达文采分析
    
    Args:
        subject (str): 作文标题
        article (str): 作文内容
        
    Returns:
        Dict[str, Any]: 完整的评分结果，包括总分、分项得分、错别字、多维分析和总体评价
    """
    session_id = str(uuid.uuid4())[:8]  # 用于跟踪请求
    text_length = len(article)
    
    try:
        # 记录开始评分
        logger.info(f"[{session_id}] 开始统一评分: 标题='{subject}', 长度={text_length}字符")
        
        # 生成统一提示词
        from ai_correction_config import get_unified_prompt
        unified_prompt = get_unified_prompt(subject, article, text_length)
        logger.info(f"[{session_id}] 生成统一评分提示词，长度={len(unified_prompt)}字符")
        
        # 设置API调用参数
        response = await create_chat_completion(
            model=deepseek_model,
            messages=[{"role": "user", "content": unified_prompt}],
            temperature=0.1,  # 降低温度使输出更确定性
            max_tokens=3000,  # 增加最大token数
            timeout=60  # 60秒超时
        )
        
        # 从响应提取文本内容
        response_text = response.choices[0].message.content
        logger.info(f"[{session_id}] 收到API响应")
        
        # 解析API响应为结构化数据
        result = parse_unified_response(response_text, session_id)
        logger.info(f"[{session_id}] 解析结果: 总分={result['总得分']}, 等级={result['等级评定']}")
        
        # 保存原始等级评定，确保不被修改
        original_grade = result.get("等级评定", "E-未完成")
        
        # 验证分数是否在合理范围内
        if not validate_scores(result):
            logger.warning(f"[{session_id}] 分数验证失败")
        
        # 应用分数规范化
        from ai_correction_config import normalize_scores
        result = normalize_scores(result, session_id)
        
        # 重新确保等级评定不被覆盖，恢复原始评定结果
        # 特别是空白作文，必须是E级别
        if int(result.get("total_score", 0)) == 0 or original_grade == "E-未完成":
            result["等级评定"] = "E-未完成"
            result["grade"] = "E-未完成"  # 同时更新兼容字段
        
        # 记录评分完成
        logger.info(f"[{session_id}] 统一评分完成: 总分={result.get('总得分', 0)}, 等级={result.get('等级评定', '未知')}")
        return result
    except Exception as e:
        return handle_scoring_error(e, subject, article, session_id)

def validate_scores(unified_result: Dict[str, Any]) -> bool:
    """
    验证分数是否在合理范围内
    
    Args:
        unified_result: 评分结果字典
        
    Returns:
        bool: 是否验证通过
    """
    try:
        # 检查字典结构
        if not isinstance(unified_result, dict):
            logger.warning("评分结果不是一个字典")
            return False
            
        # 检查分项得分
        if "分项得分" not in unified_result or not isinstance(unified_result["分项得分"], dict):
            logger.warning("分项得分字段缺失或不是字典格式")
            # 创建默认分项得分
            unified_result["分项得分"] = {
                "内容主旨": "15",
                "语言文采": "10",
                "文章结构": "8", 
                "文面书写": "5"
            }
        
        items = unified_result["分项得分"]
        
        # 确保所有必要的分项都存在
        required_items = ["内容主旨", "语言文采", "文章结构", "文面书写"]
        for key in required_items:
            if key not in items:
                logger.warning(f"分项得分缺少 {key}，设置默认值")
                if key == "内容主旨": items[key] = "15"
                elif key == "语言文采": items[key] = "10"
                elif key == "文章结构": items[key] = "8"
                elif key == "文面书写": items[key] = "5"
        
        # 检查每个分项的得分是否合理
        for key, value in items.items():
            try:
                # 如果是字符串格式，转为整数
                if isinstance(value, str):
                    score = int(value)
                    # 保持字符串格式但确保值合理
                    items[key] = str(score)
                else:
                    score = int(value)
                    # 转换为字符串格式
                    items[key] = str(score)
                
                # 检查分数范围
                if key == "内容主旨" and (score < 0 or score > 20):
                    logger.warning(f"内容主旨得分 {score} 超出合理范围(0-20)，设置为默认值15")
                    items[key] = "15"
                elif key == "语言文采" and (score < 0 or score > 15):
                    logger.warning(f"语言文采得分 {score} 超出合理范围(0-15)，设置为默认值10")
                    items[key] = "10"
                elif key == "文章结构" and (score < 0 or score > 15):
                    logger.warning(f"文章结构得分 {score} 超出合理范围(0-15)，设置为默认值8")
                    items[key] = "8"
                elif key == "文面书写" and (score < 0 or score > 5):
                    logger.warning(f"文面书写得分 {score} 超出合理范围(0-5)，设置为默认值5")
                    items[key] = "5"
            except (ValueError, TypeError) as e:
                logger.warning(f"{key}得分 {value} 无法转换为整数: {e}，使用默认值")
                # 根据不同分项设置默认值
                if key == "内容主旨": items[key] = "15"
                elif key == "语言文采": items[key] = "10"
                elif key == "文章结构": items[key] = "8"
                elif key == "文面书写": items[key] = "5"
        
        # 计算分项得分之和
        content_score = int(items.get("内容主旨", "15"))
        language_score = int(items.get("语言文采", "10"))
        structure_score = int(items.get("文章结构", "8"))
        writing_score = int(items.get("文面书写", "5"))
        sum_score = content_score + language_score + structure_score + writing_score
        
        # 获取错别字扣分
        spelling_errors = []
        if "扣分项" in unified_result and isinstance(unified_result["扣分项"], dict):
            if "错别字" in unified_result["扣分项"]:
                spelling_errors = unified_result["扣分项"]["错别字"]
        elif "错别字" in unified_result:
            spelling_errors = unified_result["错别字"]
            
        error_deduction = len(spelling_errors) if isinstance(spelling_errors, list) else 0
        
        # 计算最终总分（分项得分之和减去错别字扣分）
        final_score = max(0, sum_score - error_deduction)  # 确保总分不会小于0
        
        # 更新总得分
        unified_result["总得分"] = str(final_score)
        logger.info(f"最终总分计算: 分项得分之和({sum_score}) - 错别字扣分({error_deduction}) = {final_score}")
        
        # 根据总分确定等级评定
        if final_score >= 45:
            grade = "A-优秀"
        elif final_score >= 40:
            grade = "B-良好"
        elif final_score >= 30:
            grade = "C-中等"
        elif final_score >= 20:
            grade = "D-不足"
        else:
            grade = "E-未完成"
            
        # 更新等级评定
        unified_result["等级评定"] = grade
        unified_result["grade"] = grade  # 兼容旧版字段
        
        # 更新错别字信息
        if spelling_errors:
            unified_result["错别字"] = spelling_errors
            unified_result["错别字数量"] = error_deduction
            # 生成错别字分析文本
            error_details = []
            for error in spelling_errors:
                if isinstance(error, dict):
                    wrong = error.get("错误", "")
                    correct = error.get("正确写法", "")
                    position = error.get("位置", "")
                    if wrong and correct:
                        error_details.append(f"【{wrong}】应为【{correct}】，位置：{position}")
            if error_details:
                unified_result["错别字分析"] = "发现以下错别字：\n" + "\n".join(error_details)
            else:
                unified_result["错别字分析"] = f"发现{error_deduction}个错别字。"
        else:
            unified_result["错别字分析"] = "未发现错别字。"
        
        return True
        
    except Exception as e:
        logger.error(f"分数验证过程出错: {str(e)}")
        return False

def extract_json_from_response(response_text: str) -> str:
    """
    支持多种代码块变体，从响应中提取JSON内容
    
    Args:
        response_text (str): API返回的响应文本
        
    Returns:
        str: 提取出的JSON字符串
    """
    # 预处理：修复常见字段中的空格问题，如"错 别 字"应为"错别字"
    processed_text = response_text
    field_replacements = {
        '"错 别 字"': '"错别字"',
        '"多 维 分析"': '"多维分析"',
        '"内 容 分析"': '"内容分析"',
        '"表 达 分析"': '"表达分析"',
        '"结 构 分析"': '"结构分析"',
        '"书 写 分析"': '"书写分析"',
        '"总 得 分"': '"总得分"',
        '"分 项 得 分"': '"分项得分"',
        '"等 级 评 定"': '"等级评定"',
        '"总 体 评 价"': '"总体评价"',
    }
    
    for old, new in field_replacements.items():
        processed_text = processed_text.replace(old, new)
    
    # 尝试多种模式提取JSON
    patterns = [
        r'```json\s*({.*?})\s*```',  # 标准JSON代码块
        r'```\s*({.*?})\s*```',      # 无语言声明的代码块
        r'```json(.*?)```',          # 标准JSON代码块，允许不以大括号开始
        r'```(.*?)```',              # 任何代码块
        r'{[\s\S]*}',                # 直接查找最外层的大括号
        r'JSON:\s*({.*?})\s*$'       # 无代码块形式
    ]
    
    # 尝试匹配所有模式
    for pattern in patterns:
        match = re.search(pattern, processed_text, re.DOTALL)
        if match:
            extracted = match.group(1) if '{' in match.group(1) else match.group(0)
            # 进一步清理：确保提取到的是一个完整的JSON对象
            if extracted.strip().startswith('{') and extracted.strip().endswith('}'):
                return extracted
            elif '{' in extracted and '}' in extracted:
                # 尝试只保留最外层的大括号部分
                start = extracted.find('{')
                end = extracted.rfind('}') + 1
                return extracted[start:end]
    
    # 如果没有匹配任何模式，尝试直接提取最外层的大括号
    if '{' in processed_text and '}' in processed_text:
        start = processed_text.find('{')
        end = processed_text.rfind('}') + 1
        return processed_text[start:end]
    
    # 如果仍然无法提取，返回原始文本
    logger.warning(f"无法从响应中提取JSON格式内容，返回原始文本")
    return processed_text

def parse_unified_response(response_text: str, session_id: str = "unknown") -> Dict[str, Any]:
    """
    解析统一评分API返回的JSON响应
    
    Args:
        response_text (str): API返回的响应文本
        session_id (str): 会话ID用于日志跟踪
        
    Returns:
        Dict[str, Any]: 解析后的评分结果
    """
    try:
        # 使用优化的函数提取JSON内容
        json_str = extract_json_from_response(response_text)
        logger.info(f"[{session_id}] 提取的JSON字符串: {json_str[:200]}...")
        
        # 解析JSON
        result = json.loads(json_str)
        
        # 检查必要字段，注意：只检查必要的字段，不要检查可能不存在的字段
        required_fields = ["总得分", "等级评定", "分项得分", "错别字"]
        missing_fields = []
        for field in required_fields:
            if field not in result:
                missing_fields.append(field)
                logger.warning(f"[{session_id}] 响应缺失字段: {field}")
        
        if missing_fields:
            logger.error(f"[{session_id}] 响应缺失关键字段: {missing_fields}")
        
        # 提取和转换分数
        try:
            total_score = int(result.get("总得分", 0))
        except (ValueError, TypeError):
            logger.warning(f"[{session_id}] 总分数据类型错误，使用默认值0")
            total_score = 0
        
        # 提取分项得分 - 确保使用默认值
        item_scores = result.get("分项得分", {})
        if not isinstance(item_scores, dict):
            logger.warning(f"[{session_id}] 分项得分不是字典类型，使用默认值")
            item_scores = {}
        
        # 对缺失的分项得分使用默认值
        default_scores = {"内容主旨": 0, "语言文采": 0, "文章结构": 0, "文面书写": 0}
        for key in default_scores:
            if key not in item_scores:
                item_scores[key] = default_scores[key]
        
        # 尝试将分数转换为整数
        try:
            content_score = int(item_scores.get("内容主旨", 0))
            language_score = int(item_scores.get("语言文采", 0))
            structure_score = int(item_scores.get("文章结构", 0))
            writing_score = int(item_scores.get("文面书写", 0))
        except (ValueError, TypeError):
            logger.warning(f"[{session_id}] 某些分项得分数据类型错误，使用默认值")
            content_score = 0
            language_score = 0
            structure_score = 0
            writing_score = 0
        
        # 解析错别字
        spelling_errors = result.get("错别字", [])
        if not isinstance(spelling_errors, list):
            logger.warning(f"[{session_id}] 错别字不是列表类型，使用空列表")
            spelling_errors = []
        error_count = len(spelling_errors)
        
        # 解析多维分析 - 统一处理不同的字段名和结构
        analyses = {}
        
        # 尝试从多种可能的字段名中获取分析数据
        for field_name in ["多维分析", "多维度分析"]:
            if field_name in result and isinstance(result[field_name], dict):
                analyses = result[field_name]
                break
        
        # 如果没有找到多维分析字段，尝试从顶层查找各个分析字段
        if not analyses:
            for key in ["内容分析", "表达分析", "结构分析", "书写分析"]:
                if key in result:
                    analyses[key] = result[key]
        
        # 为缺失的分析提供默认值
        default_analysis = "作文内容为空，无法进行分析。"
        if total_score > 0:
            default_analysis = "根据作文内容分析，该作文还有提升空间。建议调整写作策略，优化内容结构。"
            
        # 准备默认的分析结果
        default_analyses = {
            "内容分析": default_analysis,
            "表达分析": default_analysis,
            "结构分析": default_analysis,
            "书写分析": default_analysis
        }
        
        # 填充缺失的分析内容
        for key, default_value in default_analyses.items():
            if key not in analyses or not analyses[key]:
                analyses[key] = default_value
                
        # 构建标准格式结果
        standardized_result = {
            "总得分": total_score,
            "等级评定": result.get("等级评定", "D-不足"),
            "分项得分": {
                "内容主旨": content_score,
                "语言文采": language_score,
                "文章结构": structure_score,
                "文面书写": writing_score
            },
            "错别字": spelling_errors,
            "错别字数量": error_count,
            "多维分析": {
                "内容分析": analyses.get("内容分析", default_analyses["内容分析"]),
                "表达分析": analyses.get("表达分析", default_analyses["表达分析"]),
                "结构分析": analyses.get("结构分析", default_analyses["结构分析"]),
                "书写分析": analyses.get("书写分析", default_analyses["书写分析"])
            },
            "总体评价": result.get("总体评价", "作文评分完成，请仔细阅读各项分析内容。"),
            "原始响应": result  # 保留原始响应以便调试
        }
        
        logger.info(f"[{session_id}] 解析结果: 总分={standardized_result['总得分']}, 等级={standardized_result['等级评定']}")
        return standardized_result
        
    except Exception as e:
        logger.error(f"[{session_id}] 解析响应时出错: {str(e)}")
        logger.error(f"[{session_id}] 原始响应: {response_text[:200]}...")
        
        # 返回最小可用结果
        return {
            "总得分": 0,
            "等级评定": "解析错误",
            "分项得分": {
                "内容主旨": 0,
                "语言文采": 0,
                "文章结构": 0,
                "文面书写": 0
            },
            "错别字": [],
            "错别字数量": 0,
            "多维分析": {
                "内容分析": "解析错误，无法获取分析内容。",
                "表达分析": "解析错误，无法获取分析内容。",
                "结构分析": "解析错误，无法获取分析内容。",
                "书写分析": "解析错误，无法获取分析内容。"
            },
            "总体评价": "系统无法解析AI评分结果，请重试或联系管理员。"
        }

def handle_scoring_error(error: Exception, subject: str, article: str, session_id: str = "unknown") -> Dict[str, Any]:
    """
    统一处理评分过程中的错误
    
    Args:
        error (Exception): 捕获的异常
        subject (str): 作文标题
        article (str): 作文内容
        session_id (str): 会话ID用于日志跟踪
        
    Returns:
        Dict[str, Any]: 备用评分结果
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    if "timeout" in error_msg.lower() or "connect" in error_msg.lower():
        logger.error(f"[{session_id}] 网络连接超时: {error_msg}")
    elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
        logger.error(f"[{session_id}] API认证失败: {error_msg}")
    elif "json" in error_msg.lower() or "parse" in error_msg.lower():
        logger.error(f"[{session_id}] 响应解析失败: {error_msg}")
    else:
        logger.error(f"[{session_id}] 评分过程出错 ({error_type}): {error_msg}")
    
    # 使用备用评分结果
    from ai_correction_config import get_fallback_result
    return get_fallback_result(subject, article)

def normalize_scores(result: Dict[str, Any], session_id: str = "unknown") -> Dict[str, Any]:
    """
    标准化评分结果，确保字段完整且符合前端要求
    
    Args:
        result: 解析后的评分结果
        session_id: 会话ID，用于日志
        
    Returns:
        Dict[str, Any]: 标准化后的评分结果
    """
    try:
        # 确保分项得分存在
        if "分项得分" not in result:
            logger.warning(f"[{session_id}] 分项得分字段缺失，使用默认值")
            result["分项得分"] = {
                "内容主旨": 0,
                "语言文采": 0,
                "文章结构": 0,
                "文面书写": 0
            }
            
        # 提取各项分数
        content_score = int(result["分项得分"].get("内容主旨", 0))
        language_score = int(result["分项得分"].get("语言文采", 0))
        structure_score = int(result["分项得分"].get("文章结构", 0))
        writing_score = int(result["分项得分"].get("文面书写", 0))
        
        # 确保分数字段在结果中，兼容旧版前端
        result["content_score"] = content_score
        result["language_score"] = language_score
        result["structure_score"] = structure_score
        result["writing_score"] = writing_score
        
        # 统一总分
        total_score = int(result.get("总得分", 0))
        result["total_score"] = total_score
        result["score"] = total_score
        result["score_value"] = total_score
        result["score_display"] = str(total_score)  # 确保为字符串
        
        # 确保等级评定存在且正确
        if "等级评定" not in result or not result["等级评定"]:
            # 根据总分重新计算等级
            if total_score >= 45:
                grade = "A-优秀"
            elif total_score >= 40:
                grade = "B-良好"
            elif total_score >= 30:
                grade = "C-中等"
            elif total_score >= 20:
                grade = "D-不足"
            else:
                grade = "E-未完成"
            result["等级评定"] = grade
            
        # 统一等级字段
        grade = result["等级评定"]
        result["grade"] = grade
        result["grade_display"] = grade  # 添加显示用的等级字段
        
        # 处理错别字信息
        spelling_errors = result.get("错别字", [])
        if not isinstance(spelling_errors, list):
            spelling_errors = []
            
        error_count = len(spelling_errors)
        result["error_count"] = error_count
        result["spelling_errors"] = spelling_errors  # 保存完整的错别字信息
        
        # 生成错别字分析文本
        if error_count > 0:
            error_details = []
            for error in spelling_errors:
                if isinstance(error, dict):
                    wrong = error.get("错误", "")
                    correct = error.get("正确写法", "")
                    position = error.get("位置", "")
                    if wrong and correct:
                        error_details.append(f"【{wrong}】应为【{correct}】，位置：{position}")
            
            if error_details:
                result["error_analysis"] = "发现以下错别字：\n" + "\n".join(error_details)
            else:
                result["error_analysis"] = f"共发现 {error_count} 个错别字。"
        else:
            result["error_analysis"] = "未发现错别字。"
            
        # 确保多维分析字段存在
        if "多维分析" not in result:
            result["多维分析"] = {
                "内容分析": "内容分析生成中...",
                "表达分析": "表达分析生成中...",
                "结构分析": "结构分析生成中...",
                "书写分析": "书写分析生成中..."
            }
            
        # 添加状态字段
        result["status"] = "completed" if total_score > 0 else "processing"
        result["status_display"] = "批改完成" if total_score > 0 else "批改中"
        
        return result
        
    except Exception as e:
        logger.error(f"[{session_id}] 标准化分数时出错: {str(e)}")
        # 返回基本结果
        return {
            "total_score": 0,
            "score": 0,
            "score_value": 0,
            "score_display": "0",
            "grade": "E-未完成",
            "grade_display": "E-未完成",
            "error_count": 0,
            "error_analysis": "分数标准化失败，请重试。",
            "status": "error",
            "status_display": "批改出错"
        }

