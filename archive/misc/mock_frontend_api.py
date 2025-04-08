#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import logging
import random
import time

# 创建Flask应用
app = Flask(__name__, static_folder='static')
CORS(app)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """首页路由"""
    return render_template('index.html')

@app.route('/test')
def test():
    """测试页面"""
    return render_template('test_upload.html')

@app.route('/correct', methods=['POST'])
def correct():
    """处理作文批改请求 - 返回固定的模拟数据"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 记录请求信息
        logger.info(f"请求内容类型: {request.content_type}")
        
        # 检查是否有文件上传
        if request.files and 'file' in request.files:
            file = request.files['file']
            logger.info(f"收到文件: {file.filename}")
            
        # 短暂延迟模拟处理时间
        time.sleep(1)
        
        # 完全匹配前端期望的格式和字段名
        result = {
            # 页面表格中显示的字段
            "字数": "800",
            "错别字扣分": "0",
            "内容主旨得分": "18",
            "表达文采得分": "17",
            "结构得分": "8.5",
            "书写得分": "4.5",
            
            # 圆圈中显示的总分和等级
            "总分": "38",
            "等级": "B",
            
            # 文本评价段落
            "总评": "这是一篇整体结构清晰、内容充实的文章，观点表达明确，但可进一步加强论述深度。",
            "综合评价": "文章有明确的主题和观点，结构较为清晰，语言表达流畅。但在论证深度和细节处理上还有提升空间。",
            "建议改进": "建议增加更多具体例子支持论点，适当拓展论述深度，丰富文章细节。",
            
            # 分析部分
            "内容主旨分析": "文章主题明确，内容充实，但可以增加具体例子来支持论点。",
            "表达文采分析": "语言表达流畅，但有一些句子可以更加精炼。语言风格上可以增加修辞手法。",
            "结构分析": "文章结构层次分明，段落组织合理，有明确的开头、正文和结尾。",
            "书写分析": "书写工整，清晰易读。",
            "错别字分析": "未发现明显错别字。",
            
            # 其他可能需要的字段
            "优点": ["观点明确", "论述清晰", "结构合理"],
            "不足": ["细节不足", "例子较少"],
            "建议": ["增加具体例子", "适当拓展论述深度", "丰富细节"]
        }
        
        logger.info(f"返回数据: {json.dumps(result, ensure_ascii=False)}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"处理错误: {str(e)}")
        return jsonify({
            "错别字扣分": "0",
            "内容主旨得分": "0",
            "表达文采得分": "0",
            "结构得分": "0",
            "书写得分": "0",
            "总分": "0",
            "等级": "F",
            "总评": f"批改失败: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("模拟API服务启动...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True) 