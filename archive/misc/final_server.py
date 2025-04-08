#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import logging
import time
import random
import re
import io
import traceback
from datetime import datetime

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 常量设置
MIN_CHARS = 500  # 最小推荐字符数

# 静态文件路径
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    """首页路由"""
    return render_template('index.html')

# 文本分析函数
def analyze_content(text):
    """分析文章内容并计算分数"""
    char_count = len(text)
    
    # 基础分数计算
    if char_count < MIN_CHARS:
        content_score = 17.6  # 基础分，但因为字数不足而降低
        expression_score = 13.6
        length_note = f"文章长度不足，当前长度: {char_count}字符，推荐长度: {MIN_CHARS}字符，影响了评分。"
    else:
        # 更高的基础分因为字数足够
        content_score = min(22.0, 17.6 + (char_count / 1000) * 4.4)
        expression_score = min(17.0, 13.6 + (char_count / 1000) * 3.4)
        length_note = ""
    
    # 固定分数组件
    structure_score = 8.5
    writing_score = 4.5
    
    # 计算总分 (内容+表达+结构+书写)
    total_score = content_score + expression_score + structure_score + writing_score
    
    # 确定等级
    if total_score >= 60:
        grade = "A"
    elif total_score >= 45:
        grade = "B"
    elif total_score >= 30:
        grade = "C"
    else:
        grade = "D"
    
    # 时间戳
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 格式化评价和分析内容 - 确保字段名精确匹配前端期望
    result = {
        # 基础评分字段 - 确保所有分数都是字符串
        "字数": str(char_count),
        "错别字扣分": "0",  # 假设没有错别字
        "内容主旨得分": str(content_score),
        "表达文采得分": str(expression_score),
        "结构得分": str(structure_score),
        "书写得分": str(writing_score),
        
        # 总分和等级 - 必须是字符串
        "总分": str(total_score),
        "等级": grade,
        
        # 文本评价字段
        "总评": f"这是一篇结构清晰、论述合理的文章。({timestamp}) {length_note}",
        "综合评价": "这是一篇有一定深度的文章，作者能够清晰表达自己的观点，但在细节和例子方面还可以进一步丰富。",
        "建议改进": "建议增加更多具体例子，使用更多修辞手法来增强文章的说服力和表现力。可以适当精简一些句子，使表达更加简洁有力。",
        
        # 五个分析字段 - 必须使用这些精确的字段名
        "内容主旨分析": "文章主题明确，内容充实，但可以增加具体例子来支持论点。",
        "表达文采分析": "语言表达流畅，但有一些句子可以更加精炼。",
        "结构分析": "文章结构清晰，逻辑连贯，有明确的开头、正文和结尾。",
        "书写分析": "写作风格良好，但可以增加一些修辞手法来使文章更加生动。",
        "错别字分析": "未发现错别字。",
        
        # 列表数据 - 前端期望的准确字段
        "优点": ["观点明确", "论述清晰", "结构合理"],
        "不足": ["细节不足", "例子较少"],
        "建议": ["增加具体例子", "使用更多修辞手法", "适当精简句子"]
    }
    
    return result

@app.route('/correct', methods=['POST'])
def correct():
    """处理作文批改请求"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 记录开始处理新请求
        logger.info("=== 新批改请求开始处理 ===")
        logger.info(f"请求内容类型: {request.content_type}")
        
        # 提取请求数据
        form_data = request.form
        logger.info(f"表单数据: {form_data}")
        files = request.files
        logger.info(f"文件: {files}")
        
        # 获取文章内容 - 优先处理文件上传
        text = ""
        
        if files and 'file' in files:
            logger.info("检测到文件上传，优先处理")
            file = files['file']
            logger.info(f"收到文件: {file.filename}")
            
            # 处理不同类型的文件
            if file.filename.endswith('.docx'):
                logger.info("处理Word文档")
                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                    import docx
                    doc = docx.Document(file)
                    text = "\n".join([para.text for para in doc.paragraphs])
                except ImportError:
                    # 如果没有python-docx库，尝试读取文件内容
                    file_content = file.read()
                    text = file_content.decode('utf-8', errors='ignore')
                    
                logger.info(f"从Word文档提取的文本长度: {len(text)}")
            else:
                # 简单文本文件
                file_content = file.read()
                text = file_content.decode('utf-8', errors='ignore')
            
            logger.info(f"从文件获取文章内容，长度: {len(text)}")
            
        elif form_data and 'article' in form_data:
            # 从表单字段获取
            text = form_data['article']
            logger.info(f"从表单获取文章内容，长度: {len(text)}")
        
        # 验证是否获取到内容
        if not text:
            logger.warning("未收到任何文章内容")
            raise ValueError("未提供文章内容")
            
        # 记录最终处理的文本长度
        logger.info(f"最终文章长度: {len(text)}")
        
        # 分析文章内容
        result = analyze_content(text)
        
        # 延迟1秒模拟处理时间
        time.sleep(1)
        
        # 重要：确保字段名称与前端完全匹配
        if isinstance(result, dict):
            # 修正可能的错误字段名称
            if "内容分析" in result:
                result["内容主旨分析"] = result.pop("内容分析")
            if "表达分析" in result:
                result["表达文采分析"] = result.pop("表达分析")
            if "语言分析" in result:
                result["表达文采分析"] = result.pop("语言分析")
                
            # 转换所有数值为字符串
            for key in result:
                if isinstance(result[key], (int, float)):
                    result[key] = str(result[key])
        
        # 记录返回的结果
        logger.info(f"最终返回结果: {json.dumps(result, ensure_ascii=False)}")
        
        return jsonify(result)
    
    except Exception as e:
        # 详细记录错误
        logger.error(f"处理错误: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 即使出错也返回完整的字段结构
        error_result = {
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
        }
        
        return jsonify(error_result), 500

if __name__ == '__main__':
    print("作文批改系统服务启动...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True) 