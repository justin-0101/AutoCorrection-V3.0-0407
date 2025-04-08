from flask import Flask, render_template, request, jsonify
import asyncio
import math
import json
import os
from test_article import *
from llm_func import *
from utils import *

app = Flask(__name__)

# 使用全局变量保存API模式选择
use_mock_api = False

@app.route('/')
def index():
    """渲染首页，显示作文批改表单"""
    return render_template('index.html', 
                        subjects=[
                            {"id": "subject_1", "text": subject_1},
                            {"id": "subject_2", "text": subject_2},
                            {"id": "subject_3", "text": subject_3}
                        ],
                        sample_articles=[
                            {"id": "article_1", "text": article_1},
                            {"id": "article_2", "text": article_2}, 
                            {"id": "article_3", "text": article_3}
                        ],
                        use_mock_api=use_mock_api)

@app.route('/toggle_mock', methods=['POST'])
def toggle_mock():
    """切换API模式（真实/模拟）"""
    global use_mock_api
    use_mock_api = not use_mock_api
    return jsonify({"success": True, "mock_mode": use_mock_api})

@app.route('/correct', methods=['POST'])
def correct_essay():
    """处理作文批改请求"""
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        subject = request.form.get('subject')
        article = request.form.get('article')
        
        if not subject or not article:
            return jsonify({"error": "作文题目和内容不能为空"}), 400
            
        # 异步运行批改任务
        result = asyncio.run(process_correction(subject, article))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def process_correction(subject, article):
    """执行作文批改流程"""
    n_words = count_chinese_characters(article)
    upper_limit, deduct_by_words = words_count_handler(n_words)

    if use_mock_api:
        # 使用模拟数据
        results = await asyncio.gather(
            mock_handler_spell_error(article),
            mock_handler_content_analysis(subject, article),
            mock_handler_express_analysis(subject, article)
        )
    else:
        # 使用真实API
        results = await asyncio.gather(
            handler_spell_error(article),
            handler_content_analysis(subject, article),
            handler_express_analysis(subject, article)
        )
    
    results_spell = results[0]
    results_content = results[1]
    results_express = results[2]

    factor = upper_limit / 60
    mark = math.ceil(factor * (int(results_express["表达文采得分"]) + int(results_content["内容主旨得分"]) + int(
        (20 - int(results_spell["错别字扣分"])))))
    detail = {"错别字解析": results_spell["解析"], "内容主旨解析": results_content["解析"], "表达文采解析": results_express["解析"]}
    
    if use_mock_api:
        summary = await mock_handler_summary(detail)
    else:
        summary = await handler_summary(detail)

    return {
        "words_count": n_words,
        "spell_error_score": results_spell['错别字扣分'],
        "spell_error_analysis": results_spell['解析'],
        "content_score": results_content['内容主旨得分'],
        "content_analysis": results_content['解析'],
        "expression_score": results_express['表达文采得分'],
        "expression_analysis": results_express['解析'],
        "total_score": mark,
        "summary": summary
    }

# 模拟API处理函数
async def mock_handler_spell_error(article: str):
    return {
        "错别字扣分": "0",
        "解析": "未发现任何错别字，本项不扣分。"
    }

async def mock_handler_content_analysis(subject: str, article: str):
    return {
        "内容主旨得分": "18",
        "解析": {
            "主旨解析": "文章紧扣主题，论述清晰，主旨明确。",
            "论点解析": "文章论点清晰，层层递进，紧扣主题。",
            "论据解析": "文章论据充实，举例恰当，论证有力。",
            "思想情感解析": "文章思想积极健康，情感真挚。"
        }
    }

async def mock_handler_express_analysis(subject: str, article: str):
    return {
        "表达文采得分": "17",
        "解析": {
            "论证手法解析": "文章运用了多种论证方法，论证有力。",
            "引经据典解析": "文章适当引用了典故和名言，增强了文章的说服力。",
            "修辞手法解析": "文章运用了比喻、排比等修辞手法，语言生动形象。"
        }
    }

async def mock_handler_summary(detail: dict):
    return """总评：
本篇作文立意明确，主题突出，内容充实，表达流畅。在内容方面，文章主旨鲜明，论点清晰，论据充分，思想健康。在表达方面，文章运用了多种修辞手法，语言生动形象，表达得体。
建议：
1. 可以增加一些具体事例，使论据更加丰富；
2. 可以进一步丰富修辞手法的运用，使表达更加生动。
总体而言，这是一篇很好的文章，主题突出，论证有力，表达得体。"""

if __name__ == '__main__':
    # 创建templates和static目录（如果不存在）
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    # 启动Flask应用
    app.run(debug=True, port=5000)