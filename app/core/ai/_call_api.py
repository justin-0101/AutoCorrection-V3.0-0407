from typing import List, Dict
import httpx
import json
import traceback
from datetime import datetime

class DeepseekClient:
    def __init__(self, api_url, model, api_config, client):
        self.api_url = api_url
        self.model = model
        self.api_config = api_config
        self.client = client

    async def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> Dict:
        """
        调用API并处理响应
        
        Args:
            messages: 消息列表
            
        Returns:
            Dict: API响应
            
        Raises:
            APIError: API调用错误
        """
        try:
            print(f"[DeepseekClient] 开始API调用，消息数: {len(messages)}")
            logger.info(f"[DeepseekClient] 开始API调用，消息数: {len(messages)}")
            
            # 记录API请求配置
            api_config = {
                "url": self.api_url,
                "model": self.model,
                "temperature": self.api_config.get("temperature", 0.1),
                "timeout": self.client.timeout.connect
            }
            print(f"[DeepseekClient] API配置: {api_config}")
            logger.info(f"[DeepseekClient] API配置: {api_config}")
            
            # 发起API请求
            print(f"[DeepseekClient] 发送请求到 {self.api_url}")
            
            # 创建完整的API请求参数
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.api_config.get("temperature", 0.1),
                **kwargs
            }
            
            # API请求开始时间
            api_start_time = datetime.now()
            
            # 打印请求前的时间戳
            print(f"[DeepseekClient] 发送API请求时间: {api_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            
            # 调用API
            response = await self.client.chat.completions.create(**request_params)
            
            # API请求结束时间和耗时
            api_end_time = datetime.now()
            api_elapsed = (api_end_time - api_start_time).total_seconds()
            
            # 打印请求后的时间戳和耗时
            print(f"[DeepseekClient] 收到API响应时间: {api_end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            print(f"[DeepseekClient] API请求总耗时: {api_elapsed:.2f}秒")
            
            # 格式化响应
            formatted_response = self.format_response(response)
            
            # 打印响应摘要
            content_length = len(formatted_response.get("content", ""))
            print(f"[DeepseekClient] API响应内容长度: {content_length}字符")
            
            return formatted_response
            
        except httpx.RequestError as e:
            print(f"[DeepseekClient] API请求错误: {str(e)}")
            logger.error(f"[DeepseekClient] API请求错误: {str(e)}")
            raise APIError(f"API请求错误: {str(e)}")
            
        except httpx.HTTPStatusError as e:
            print(f"[DeepseekClient] API状态错误: {e.response.status_code} - {str(e)}")
            logger.error(f"[DeepseekClient] API状态错误: {e.response.status_code} - {str(e)}")
            raise APIError(f"API状态错误: {e.response.status_code} - {str(e)}")
            
        except json.JSONDecodeError as e:
            print(f"[DeepseekClient] JSON解析错误: {str(e)}")
            logger.error(f"[DeepseekClient] JSON解析错误: {str(e)}")
            raise APIError(f"JSON解析错误: {str(e)}")
            
        except Exception as e:
            print(f"[DeepseekClient] API调用异常: {str(e)}")
            logger.error(f"[DeepseekClient] API调用异常: {str(e)}")
            logger.error(f"[DeepseekClient] 异常详情: {traceback.format_exc()}")
            raise APIError(f"API调用异常: {str(e)}") 