# -*- coding: utf-8 -*-
"""
简化版的作文批改服务器，仅用于测试
"""
from flask import Flask, request, jsonify
import logging

# 设置基本变量
MIN_CHARS = 500

# 辅助函数：确保分数是字符串类型
def to_string(value):
    return str(value)

# 辅助函数：标准化分数字段
def normalize_scores(result):
    """确保所有分数字段以字符串形式返回"""
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
    
    return result

# 创建Flask应用
app = Flask(__name__)

@app.route('/')
def index():
    return "简化版作文批改服务器运行中"

@app.route('/correct', methods=['POST'])
def correct():
    """处理作文批改请求"""
    data = request.json
    
    # 提取文章内容
    article = data.get('article', '')
    
    # 简单检查字数
    if len(article) < MIN_CHARS:
        return jsonify({
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
        })
    
    # 模拟AI评分结果
    result = {
        "content_score": 22,
        "language_score": 17,
        "structure_score": 8.5,
        "writing_score": 4.5,
        "total_score": 45,
        "总分": 45,
        "comments": "测试评论",
        "strengths": ["观点明确", "论述清晰"],
        "weaknesses": ["细节不足"],
        "suggestions": ["建议增加具体例子"],
        "level": "A",
        "sub_item_scores": {
            "论点": 22,
            "结构": 17,
            "语言": 8.5,
            "文笔": 4.5
        }
    }
    
    # 确保所有分数返回为字符串类型
    result = normalize_scores(result)
    
    return jsonify(result)

if __name__ == '__main__':
    print("简化版作文批改服务器启动...")
    print("访问地址：http://127.0.0.1:5000")
    app.run(host='0.0.0.0', debug=True) 