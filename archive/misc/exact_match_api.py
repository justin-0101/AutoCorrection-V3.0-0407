#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import json
import logging
import time

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """首页路由"""
    return "精确匹配API服务 - 请使用POST /correct 接口上传文件进行批改"

@app.route('/correct', methods=['POST'])
def correct():
    """处理作文批改请求 - 使用完全匹配前端期望的字段名和格式"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 记录请求信息
        logger.info(f"请求内容类型: {request.content_type}")
        if request.files and 'file' in request.files:
            file = request.files['file']
            logger.info(f"收到文件: {file.filename}")
        
        # 延迟1秒模拟处理
        time.sleep(1)
        
        # 注意字段名必须完全匹配前端期望
        mock_result = {
            # 这些是表格中显示的字段 - 全部转换为字符串
            "字数": "800",
            "错别字扣分": "0",
            "内容主旨得分": "18",
            "表达文采得分": "17",
            "结构得分": "8.5",
            "书写得分": "4.5",
            
            # 圆圈显示的总分和等级
            "总分": "38",
            "等级": "B",
            
            # 下方显示的分析类文字
            "总评": "这是一篇结构清晰的文章，观点表达明确。",
            "综合评价": "文章有明确的主题和观点，结构较为清晰，语言表达流畅。",
            "建议改进": "建议增加具体例子支持论点，适当拓展论述深度。",
            
            # 前端期望的具体分析字段 - 使用这些精确的字段名
            "内容主旨分析": "文章主题明确，内容充实，可增加例子支持论点。",
            "表达文采分析": "语言表达流畅，可增加修辞手法使文章更生动。",
            "结构分析": "文章结构清晰，段落组织合理，有明确开头和结尾。",
            "书写分析": "书写工整，清晰易读。",
            "错别字分析": "未发现错别字。",
            
            # 前端期望的列表数据
            "优点": ["观点明确", "论述清晰", "结构合理"],
            "不足": ["细节不足", "例子较少"],
            "建议": ["增加具体例子", "使用更多修辞手法", "适当精简句子"]
        }
        
        logger.info(f"返回数据: {json.dumps(mock_result, ensure_ascii=False)}")
        return jsonify(mock_result)
        
    except Exception as e:
        logger.error(f"处理错误: {str(e)}")
        # 即使出错也返回完整的字段结构
        return jsonify({
            "字数": "0",
            "错别字扣分": "0",
            "内容主旨得分": "0",
            "表达文采得分": "0",
            "结构得分": "0",
            "书写得分": "0",
            "总分": "0",
            "等级": "F",
            "总评": f"批改失败: {str(e)}",
            "综合评价": "无法评价",
            "建议改进": "请重新提交",
            "内容主旨分析": "无法分析",
            "表达文采分析": "无法分析",
            "结构分析": "无法分析",
            "书写分析": "无法分析",
            "错别字分析": "无法分析",
            "优点": [],
            "不足": [],
            "建议": []
        }), 500

if __name__ == '__main__':
    print("精确匹配API服务启动...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True) 