#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import logging
import random
import datetime
import time
import traceback

# 设置常量
MIN_CHARS = 500

# 辅助函数：确保分数是字符串类型
def to_string(value):
    """将任何值转换为字符串"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    else:
        return str(value)

# 辅助函数：标准化分数字段
def normalize_scores(result):
    """确保所有分数字段以字符串形式返回"""
    if not isinstance(result, dict):
        return result
        
    score_fields = [
        'content_score', 'language_score', 'structure_score', 
        'writing_score', 'total_score', '总分'
    ]
    
    for field in score_fields:
        if field in result and result[field] is not None:
            result[field] = to_string(result[field])
            
    # 处理分项得分
    if 'sub_item_scores' in result and isinstance(result['sub_item_scores'], dict):
        for key, value in result['sub_item_scores'].items():
            result['sub_item_scores'][key] = to_string(value)
    
    # 处理分项得分的中文版本
    if '分项得分' in result and isinstance(result['分项得分'], dict):
        for key, value in result['分项得分'].items():
            result['分项得分'][key] = to_string(value)
    
    return result

# 创建Flask应用
app = Flask(__name__)
CORS(app)
print("已应用基本CORS配置")

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 警告信息
print("警告：未能加载python-docx库，将使用替代方法")

@app.route('/')
def index():
    """首页路由 - 使用原始的前端模板"""
    return render_template('index.html')

@app.route('/test')
def test():
    """测试页面路由"""
    return render_template('test_upload.html')

@app.route('/correct', methods=['POST'])
def correct():
    """处理作文批改请求"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 获取JSON数据
        data = request.get_json()
        
        # 提取文章内容
        article = data.get('article', '')
        
        # 简单检查字数
        if len(article) < MIN_CHARS:
            response = {
                "error": f"文章长度不足，最小要求{MIN_CHARS}字符",
                "content_score": "0",
                "language_score": "0",
                "structure_score": "0",
                "writing_score": "0",
                "total_score": "0",
                "comments": "文章长度不足",
                "strengths": [],
                "weaknesses": ["文章太短"],
                "suggestions": ["增加内容至少达到500字符"]
            }
            return jsonify(normalize_scores(response))
        
        # 延迟3秒模拟处理时间
        time.sleep(1)
        
        # 模拟AI评分结果
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "content_score": 22,
            "language_score": 17,
            "structure_score": 8.5,
            "writing_score": 4.5,
            "total_score": 45 + random.randint(0, 5),
            "总分": 45 + random.randint(0, 5),
            "comments": f"这是一篇结构清晰、论述合理的文章。({current_time})",
            "content_analysis": "文章主题明确，内容充实，但可以增加具体例子来支持论点。",
            "structure_analysis": "文章结构清晰，逻辑连贯，有明确的开头、正文和结尾。",
            "language_analysis": "语言表达流畅，但有一些句子可以更加精炼。",
            "writing_analysis": "写作风格良好，但可以增加一些修辞手法来使文章更加生动。",
            "strengths": ["观点明确", "论述清晰", "结构合理"],
            "weaknesses": ["细节不足", "例子较少"],
            "suggestions": ["建议增加具体例子", "可以使用更多修辞手法", "适当精简部分句子"],
            "level": "A",
            "sub_item_scores": {
                "论点": 22,
                "结构": 17,
                "语言": 8.5,
                "文笔": 4.5
            },
            "分项得分": {
                "论点": 22,
                "结构": 17,
                "语言": 8.5,
                "文笔": 4.5
            }
        }
        
        # 确保所有分数返回为字符串类型
        result = normalize_scores(result)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"批改过程中出错: {str(e)}")
        error_result = {
            "error": f"批改过程中出错: {str(e)}",
            "content_score": "0",
            "language_score": "0",
            "structure_score": "0", 
            "writing_score": "0",
            "total_score": "0",
            "comments": "服务器处理错误"
        }
        return jsonify(normalize_scores(error_result))

if __name__ == '__main__':
    print("作文批改系统服务启动...")
    print("访问地址：http://127.0.0.1:5000")
    app.run(host='0.0.0.0', debug=True) 