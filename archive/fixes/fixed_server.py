# -*- coding: utf-8 -*-

﻿# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_file

import asyncio



# 导入评分结果转换功能

try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")

    from score_conversion import normalize_scores

except ImportError:

    # 如果无法导入，定义一个简单的替代函数

    def normalize_scores(result_dict):

        """确保分数字段都是字符串类型"""

        if not isinstance(result_dict, dict):

            return result_dict

            

        # 转换需要的字段

        score_fields = [

            'total_score', 'score', 'content_score', 'language_score', 

            'structure_score', 'writing_score'

        ]

        

        for field in score_fields:

            if field in result_dict and result_dict[field] is not None:

                if not isinstance(result_dict[field], str):

                    result_dict[field] = str(result_dict[field])

        

        return result_dict



import math

import json

import os

import tempfile

import base64

from werkzeug.utils import secure_filename

import docx2txt

import PyPDF2

from PIL import Image

from pdf2image import convert_from_path

from test_article import *

from llm_func import *

from utils import *

import requests

from dotenv import load_dotenv

import time

import random

import re

import subprocess

import os

import json

import random

import time

import uuid

import tempfile

import base64

import asyncio

import datetime

from pathlib import Path

from io import BytesIO

import sys

import logging

try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")

    from flask_cors import CORS

    print("鎴愬姛瀵煎叆 flask_cors 妯″潡")

except ImportError:

    print("璀﹀憡: flask_cors 妯″潡鏈壘鍒帮紝CORS鍔熻兘灏嗕笉鍙敤")

    # 鍒涘缓涓€涓畝鍗曠殑CORS鏇夸唬绫?

    class CORS:

        def __init__(self, app=None, **kwargs):

            if app:

                self.init_app(app)

        

        def init_app(self, app):

            @app.after_request

            def add_cors_headers(response):

                response.headers['Access-Control-Allow-Origin'] = '*'

                response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'

                response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'

                return response

            print("已应用基本CORS配置)
"


# 瀵煎叆鏂囨。澶勭悊妯″潡

import docx2txt  # 鐢ㄤ簬澶勭悊.docx鏂囦欢

try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")

    import docx  # 灏濊瘯瀵煎叆python-docx搴?

    DOCX_AVAILABLE = True

except ImportError:

    print("璀﹀憡锛氭湭鑳藉鍏ython-docx搴擄紝灏嗕娇鐢ㄦ浛浠ｆ柟娉?)
"
    DOCX_AVAILABLE = False



# 瀵煎叆鏂扮殑OCR鏈嶅姟妯″潡

from complete_ocr_fix import OcrService



# 鍔犺浇鐜鍙橀噺

load_dotenv()



# 鐧惧害鍗冨竼API閰嶇疆

QIANFAN_AK = os.getenv("QIANFAN_AK")

QIANFAN_SK = os.getenv("QIANFAN_SK")



# 闃块噷鍗冮棶API閰嶇疆

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY.startswith("your_") or len(DASHSCOPE_API_KEY) < 10:

    # 濡傛灉鐜鍙橀噺鍊间笉姝ｇ'锛岃褰曡鍛婅€屼笉鏄繑鍥炵殑DASHSCOPE_API_KEY鐜鍙橀噺锛岃鍦╡nv鏂囦欢涓繑鍥炵殑鍒嗘瀽锛岄噸鐐圭獊鍑鸿瘎鍒嗗拰涓昏緫

    print("璀﹀憡: 鏈繑鍥炵殑DASHSCOPE_API_KEY鐜鍙橀噺锛岃鍦╡nv鏂囦欢涓繑鍥炵殑鍒嗘瀽锛岄噸鐐圭獊鍑鸿瘎鍒嗗拰涓昏緫")



DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-vl-max")  # 浣跨敤qwen-vl-max



# OCR閰嶇疆

OCR_PROVIDER = "qwen"  # 鍙夋嫨 "qwen", "tesseract", "mock"



# 鎵撳嵃璋冭瘯淇℃伅

print(f"鍔犺浇鐜鍙橀噺缁撴灉:")

print(f"DASHSCOPE_API_KEY: {'宸茶闀垮害:'+str(len(DASHSCOPE_API_KEY))+'瀛楃闁)' if DASHSCOPE_API_KEY else '鏈繑鍥炵殑鍒嗘瀽'}")
)
print(f"DASHSCOPE_MODEL: {DASHSCOPE_MODEL}")

print(f"OCR妯″紡: {OCR_PROVIDER}")



# 鍒涘缓Flask搴旂敤

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 闄愬埗涓婁紶鏂囦欢澶у皬6MB



# 娣诲姞CORS鏀寔锛屽厑璁告墍鏈夊煙鍚嶈闂?

CORS(app)



# 鍏佽鐨勬枃浠舵墿灞曞悕

ALLOWED_EXTENSIONS = {

    'txt': '鏂囨湰鏂囦欢',

    'text': '鏂囨湰鏂囦欢',

    'doc': 'Word鏂囨。',

    'docx': 'Word鏂囨。',

    'pdf': 'PDF鏂囨。',

    'jpg': '鍥剧墖',

    'jpeg': '鍥剧墖',

    'png': '鍥剧墖',

    'bmp': '鍥剧墖',

    'gif': '鍥剧墖'

}



# 鍒涘缓OCR鏈嶅姟瀹炰緥

ocr_service = OcrService()



# 璁剧疆涓婁紶鏂囦欢淇濆瓨鐩綍

UPLOAD_FOLDER = 'static/uploads'

if not os.path.exists(UPLOAD_FOLDER):

    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



# 鍏佽鐨勬枃浠剁被鍨嬫鏌?

def allowed_file(filename):

    print(f"妫€鏌ユ枃浠剁被鍨?{filename}")

    if '.' not in filename:

        print(f"鏈壘鍒版枃浠舵墿灞曞悕: {filename}")

        return False

    

    ext = filename.rsplit('.', 1)[1].lower()

    print(f"鏂囦欢鎵╁睍鍚?{ext}锛屾槸鍚︽敮鎸?{ext in ALLOWED_EXTENSIONS}")

    return ext in ALLOWED_EXTENSIONS



# 涓婚〉璺敱

@app.route('/')

def index():

    return render_template('index.html')



# 娴嬭瘯椤甸潰璺敱

@app.route('/test')

def test_page():

    return render_template('test.html')



# 鎵规敼鏂囩珷API

@app.route('/correct', methods=['POST'])

def correct():

    """澶勭悊浣滄枃鎵规敼璇锋眰"""

    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        # 妫€鏌ヨ姹備腑鏄惁鍖呭惈鏂囦欢鎴栨枃绔犲唴瀹?

        subject = request.form.get('subject', '')

        article = request.form.get('article', '')

        

        # 娣诲姞鏇磋織

        print(f"鏀跺埌鎵规敼璇锋眰: 鏍囬織={subject}, 鏂囩珷闀垮害={len(article) if article else 0}")

        print(f"鎺ユ敹鍒扮殑鏂囦欢: {request.files}")

        

        # 澶勭悊涓婁紶鐨勬枃浠?

        essay_text = article

        temp_file = None

        

        if 'file' in request.files:

            file = request.files['file']

            if file and file.filename:

                filename = file.filename

                secure_name = secure_filename(filename)

                file_ext = os.path.splitext(secure_name)[1].lower()

                

                print(f"鎺ユ敹鍒版枃浠?{filename}, 瀹夊叏鏂囦欢鍚?{secure_name}, 鎵╁睍鍚?{file_ext}")

                print(f"鏂囦欢鍐呭绫诲瀷: {file.content_type}, mimetype: {file.mimetype}")

                file_size = len(file.read())

                print(f"鏂囦欢澶у皬: {file_size} 瀛楄妭")

                file.seek(0)  # 閲嶇疆鏂囦欢鎸囬拡

                

                # 妫€鏌ユ枃浠剁被鍨?

                if not allowed_file(secure_name):

                    print(f"涓嶆敮鎸佺殑鏂囦欢绫诲瀷: {file_ext}, 鏂囦欢鍚?{filename}, 瀹夊叏鏂囦欢鍚?{secure_name}")

                    return jsonify(normalize_scores({))
                        "success": False,

                        "error": f"涓嶆敮鎸佺殑鏂囦欢绫诲瀷: {file_ext}"

                    })

                

                # 鍒涘缓涓存椂鏂囦欢

                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")

                    temp_file = tempfile.NamedTemporaryFile(delete=False)

                    file.save(temp_file.name)

                    temp_file.close()

                    print(f"鍒涘缓涓存椂鏂囦欢: {temp_file.name}")

                

                    # 鏍规嵁鏂囦欢绫诲瀷閫夋嫨涓嶅悓鐨勬枃鏈彁鍙栨柟娉?

                    if file_ext in ['.txt', '.text'] or not file_ext:

                        print("澶勭悊鏂囨湰鏂囦欢")

                        essay_text = extract_text_from_txt(temp_file.name)

                    elif file_ext in ['.doc', '.docx']:

                        print("澶勭悊Word鏂囨。")

                        essay_text = extract_text_from_docx(temp_file.name)

                    elif file_ext == '.pdf':

                        print("澶勭悊PDF鏂囦欢")

                        # 浠庣幆澧冨彉閲忚幏鍙朞CR妯″紡锛岄粯璁や负鏈緢灏戯紝鍙兘鏄壂鎻忓瀷PDF锛屽皾璇曚娇鐢∣CR

                        ocr_mode = os.getenv("OCR_MODE", "local")

                        print(f"OCR妯″紡: {ocr_mode}")

                        essay_text = extract_text_from_pdf(temp_file.name)

                    elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:

                        print("澶勭悊鍥剧墖鏂囦欢")

                        # 浠庣幆澧冨彉閲忚幏鍙朞CR妯″紡锛岄粯璁や负鏈緢灏戯紝鍙兘鏄壂鎻忓瀷PDF锛屽皾璇曚娇鐢∣CR

                        ocr_mode = os.getenv("OCR_MODE", "local")

                        print(f"OCR妯″紡: {ocr_mode}")

                        essay_text = extract_text_from_image(temp_file.name)

                    else:

                        os.unlink(temp_file.name)

                        return jsonify(normalize_scores({))
                            "success": False,

                            "error": f"涓嶆敮鎸佺殑鏂囦欢绫诲瀷: {file_ext}"

                        })

                    

                    print(f"鎻愬彇鐨勬枃鏈暱搴?{len(essay_text) if essay_text else 0}")

                    print(f"鎻愬彇鐨勬枃鏈暱瑙?{essay_text[:100]}...")

                except Exception as e:

                    print(f"澶勭悊鏂囦欢鏃跺嚭閿?{e}")

                    if temp_file:

                        try:
                            pass  # 自动修复的空块
                        except Exception as e:
                            logger.error(f"发生错误: {str(e)}")
                        except Exception as e:
                            logger.error(f"发生错误: {str(e)}")

                            os.unlink(temp_file.name)

                        except:

                            pass

                    return jsonify(normalize_scores({))
                        "success": False,

                        "error": f"澶勭悊鏂囦欢鏃跺嚭閿?{str(e)}"

                    })

                finally:

                    # 娓呯悊涓存椂鏂囦欢

                    if temp_file:

                        try:
                            pass  # 自动修复的空块
                        except Exception as e:
                            logger.error(f"发生错误: {str(e)}")
                        except Exception as e:
                            logger.error(f"发生错误: {str(e)}")

                            os.unlink(temp_file.name)

                        except:

                            pass

        

        # 纭繚鏈夋枃绔犲唴瀹?

        if not essay_text or len(essay_text) < 10:

            print("鏂囩珷鍐呭绫诲涓虹┖鎴栧お鐭?)
"
            return jsonify(normalize_scores({))
                "success": False,

                "error": "鏂囩珷鍐呭绫诲涓虹┖鎴栧お鐭紝璇锋鏌ヤ笂浼犵殑鏂囦欢鎴栫洿鎺ヨ緭鍏ユ枃绔犲唴瀹?
"
            })

        

        # 鎵撳嵃鏂囩珷闀垮害

        print(f"鍑嗗鎵规敼鐨勬枃绔犻暱搴?{len(essay_text)}")

        

        # 寮傛璋冪敤鎵规敼澶勭悊鍑芥暟

        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

        result = # 异步调用批改处理函数

        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(process_correction(subject, essay_text))

        loop.close()

        

        # 确保所有分数都是字符串格式

        result = normalize_scores(result)

        

        return jsonify(normalize_scores(result))

    except Exception as e:

        import traceback

        error_type = type(e).__name__

        error_msg = str(e)

        trace = traceback.format_exc()

        print(f"鎵规敼杩囩▼涓嚭閿欑被鍨? {error_type}")

        print(f"鎵规敼杩囩▼涓嚭閿? {error_msg}")

        print(f"閿欒杩芥函: {trace}")

        return jsonify(normalize_scores({))
            "success": False,

            "error": f"鎵规敼杩囩▼涓嚭閿?{str(e)}"

        })



# 鏂囩珷鎵规敼澶勭悊鍑芥暟

async def process_correction(title, essay):

    """澶勭悊浣滄枃鎵规敼鐨勬牳蹇冮€昏緫"""

    MIN_CHARS = 500  # 鏈灏忓瓧绗︽暟瑕佹眰

    

    # 鏍囧噯鍖栧弬鏁?

    essay_text = essay or ""

    subject = title or "鏃犳爣棰樹綔鏂?
"
    

    # 绠鍗曠殑鏂囨湰鍒嗘瀽

    word_count = len(essay_text)

    

    print(f"鍑嗗鎵规敼鐨勬枃绔犻暱搴?{len(essay_text)}")

    

    # 濡傛灉鏂囩珷鍐呭绫诲澶煭锛岀粰鍑哄弸濂芥彁绀?

    if len(essay_text) < 50:

        return {

            "success": False,

            "error": "鏂囩珷鍐呭绫诲澶煭锛屾棤娉曡繘琛屾湁鏁堟壒鏀?,
"
            "score": "0",

            "score_display": "鏃犳晥",

            "score_value": 0

        }

    

    # 浣跨敤Deepseek AI杩涜鎵规敼

    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        # 鍑嗗鎵规敼鎻愮ず

        prompt = f"""
"
        根据以下作文进行评价与打分：



        作文题目：{title}

        作文内容：

        {essay_text}



        字数要求：不少于{MIN_CHARS}字。当前字数：{word_count}字。



        评分标准参考广东中学语文考试：

        总分50分制。给定等级(A/B/C/D)，A为优秀(40-50分)，B为良好(30-39分)，C为及格(20-29分)，D为不及格(0-19分)。



        必须以JSON格式返回结果，结构如下：

        {{

        "总得分": "45",

        "等级评定": "A-优秀",

        "分项得分": {{

            "内容主旨": "22",

            "语言文采": "17",

            "文章结构": "8.5",

            "文面书写": "4.5"

        }},

        "总体评价": ""

        }}

        """
"
        

        print("姝ｅ湪璋冪敤Deepseek AI杩涜鎵规敼...")

        

        # 璋冪敤llm_func.py涓殑model鍑芥暟鑾峰彇Deepseek璇勫垎缁撴灉

        start_time = time.time()  # 璁板綍API璋冪敤寮€濮嬫椂闂?

        response = await model([
)
            {"role": "system", "content": "浣犳槸涓€浣嶄笓涓氱殑涓璇枃鏁欏笀锛屾搮闀块珮鏁堣瘎鍒ゅ鐢熶綔鏂囥€傝鎻愪緵绠€鏄庢壖瑕佺殑鍒嗘瀽锛岄噸鐐圭獊鍑鸿瘎鍒嗗拰涓昏緫
"
        ])

        

        api_time = time.time() - start_time  # 璁＄畻API璋冪敤鑰楁椂

        print(f"Deepseek API璋冪敤鑰楁椂: {api_time:.2f}绉?)
"
        

        if not response or not response.choices:

            raise Exception("Deepseek API杩斿洖缁撴灉涓虹┖")

            

        # 浠巖esponse瀵硅薄涓纭彁鍙栨枃鏈唴瀹?

        response_text = response.choices[0].message.content

        print("Deepseek鎵规敼缁撴灉:", response_text[:200] + "...")

        

        # 灏濊瘯瑙ｆ瀽JSON鍝嶅簲

        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")

            # 灏濊瘯鎻愬彇JSON閮ㄥ垎锛堝鏋滆繑鍥炵殑涓嶆槸绾疛SON锛?

            json_start = response_text.find('{')

            json_end = response_text.rfind('}') + 1

            

            start_parse_time = time.time()  # 璁板綍瑙ｆ瀽寮€濮嬫椂闂?

            

            if json_start >= 0 and json_end > json_start:

                json_text = response_text[json_start:json_end]

                ai_correction = json.loads(json_text)

            else:

                # 濡傛灉娌℃湁鎵惧埌JSON锛屽皾璇曠洿鎺ヨВ鏋愭暣涓搷搴?

                ai_correction = json.loads(response_text)

            

            parse_time = time.time() - start_parse_time  # 璁＄畻瑙ｆ瀽鑰楁椂

            print(f"JSON瑙ｆ瀽鑰楁椂: {parse_time:.2f}绉?)
"
            

            print("Deepseek鎵规敼缁撴灉瑙ｆ瀽鎴愬姛")

            

            # 瀹夊叏鍦版彁鍙栧垎鏁板拰璇勫畾锛岄伩鍏嶆牸寮忓寲闂

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                # 鎻愬彇鎬诲垎

                total_score = 0

                if '鎬诲緱鍒? in ai_correction:

                    total_score_value = ai_correction['鎬诲緱鍒?]

                    if isinstance(total_score_value, str):

                        total_score = int(total_score_value.strip())

                    else:

                        total_score = int(total_score_value)

                

                # 鎻愬彇绛夌骇

                level = 'C'

                if '绛夌骇璇勫畾' in ai_correction:

                    level = ai_correction['绛夌骇璇勫畾']

                    if '-' in level:

                        level = level.split('-')[0]

                

                # 瀹夊叏澶勭悊鍒嗛」寰楀垎

                content_score = 0

                language_score = 0

                structure_score = 0

                writing_score = 0

                

                if '鍒嗛」寰楀垎' in ai_correction and isinstance(ai_correction['鍒嗛」寰楀垎'], dict):

                    鍒嗛」寰楀垎 = ai_correction['鍒嗛」寰楀垎']

                    

                    # 鍐呭涓绘棬寰楀垎

                    if '鍐呭涓绘棬' in 鍒嗛」寰楀垎:

                        content_value = 鍒嗛」寰楀垎['鍐呭涓绘棬']

                        if isinstance(content_value, str):

                            try:
                                pass  # 自动修复的空块
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")

                                content_score = float(content_value.strip())

                            except:

                                content_score = 0

                        else:

                            content_score = float(content_value)

                    

                    # 璇繡█鏂囬噰寰楀垎

                    if '璇繡█鏂囬噰' in 鍒嗛」寰楀垎:

                        language_value = 鍒嗛」寰楀垎['璇繡█鏂囬噰']

                        if isinstance(language_value, str):

                            try:
                                pass  # 自动修复的空块
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")

                                language_score = float(language_value.strip())

                            except:

                                language_score = 0

                        else:

                            language_score = float(language_value)

                    

                    # 鏂囩珷缁撴瀯寰楀垎

                    if '鏂囩珷缁撴瀯' in 鍒嗛」寰楀垎:

                        structure_value = 鍒嗛」寰楀垎['鏂囩珷缁撴瀯']

                        if isinstance(structure_value, str):

                            try:
                                pass  # 自动修复的空块
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")

                                structure_score = float(structure_value.strip())

                            except:

                                structure_score = 0

                        else:

                            structure_score = float(structure_value)

                    

                    # 鏂囬潰涔﹀啓寰楀垎

                    if '鏂囬潰涔﹀啓' in 鍒嗛」寰楀垎:

                        writing_value = 鍒嗛」寰楀垎['鏂囬潰涔﹀啓']

                        if isinstance(writing_value, str):

                            try:
                                pass  # 自动修复的空块
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")

                                writing_score = float(writing_value.strip())

                            except:

                                writing_score = 0

                        else:

                            writing_score = float(writing_value)

            except Exception as extract_error:

                print(f"鎻愬彇寰楀垎鏁版嵁鍑洪敊: {extract_error}")

                # 璁剧疆榛樿鍊?

                total_score = 35

                level = 'C'

                content_score = 8.0

                language_score = 7.0

                structure_score = 7.0

                writing_score = 4.0

            

            # 閿欏埆瀛楀垎鏋?- 浼樺寲澶勭悊閫昏緫

            errors = []

            if '閿欏埆瀛楀垎鏋? in ai_correction and isinstance(ai_correction['閿欏埆瀛楀垎鏋?], list):

                # 鎻愬彇閿欏埆瀛楀垎鏋愰噷鐨勫垪琛ㄥ唴瀹?

                error_list = ai_correction['閿欏埆瀛楀垎鏋?]

                

                # 濡傛灉鎵ｅ垎椤逛腑鏈夊祵濂楃粨鏋?

                if '鎵ｅ垎椤? in ai_correction and isinstance(ai_correction['鎵ｅ垎椤?], dict) and '閿欏埆瀛楀垎鏋? in ai_correction['鎵ｅ垎椤?]:

                    if isinstance(ai_correction['鎵ｅ垎椤?]['閿欏埆瀛楀垎鏋?], list):

                        error_list = ai_correction['鎵ｅ垎椤?]['閿欏埆瀛楀垎鏋?]

                

                # 鍙鐞嗗墠5涓敊鍒瓧锛岄伩鍏嶈繃澶氬鐞?

                for error in error_list[:5]:

                    if isinstance(error, dict):

                        # 鑾峰彇閿欒鍜屼慨姝ｆ枃鏈?

                        error_text = error.get('閿欒鍜屼慨姝ｆ枃鏈?, '')

                        position_text = error.get('浣嶇疆', '')

                        correction_text = error.get('淇', error.get('姝ｇ'鍐欐硶', ''))

                        context = error.get('涓婁笅鏂?, '')

                        

                        # 濡傛灉娌℃湁涓婁笅鏂囦絾鏈変綅缃俊鎭紝鍙互浣跨敤浣嶇疆浣滀负涓婁笅鏂?

                        if not context and position_text:

                            context = position_text

                            

                        # 纭繚鏈夋湁鏁堢殑閿欏埆瀛椾俊鎭?

                        if error_text and correction_text:

                            err_obj = {

                                "error": error_text,

                                "correction": correction_text,

                                "position": position_text,

                                "context": context

                            }

                            errors.append(err_obj)

            

            # 浼樼己鐐逛笌寤鸿 - 绠€鍖栧鍜屼慨姝ｆ枃鏈?

            strengths = ai_correction.get('浣滄枃浼樼偣', [])

            if not isinstance(strengths, list):

                strengths = [strengths] if strengths else []

            

            weaknesses = ai_correction.get('浣滄枃涓嶈冻', [])

            if not isinstance(weaknesses, list):

                weaknesses = [weaknesses] if weaknesses else []

            

            suggestions = ai_correction.get('鏀硅繘寤鸿', [])

            if not isinstance(suggestions, list):

                suggestions = [suggestions] if suggestions else []

            

            comments = ai_correction.get('鎬讳綋璇勪环', '')

            

            # 鎻愬彇琛ㄨ揪鏂囬噰鍒嗘瀽 - 绠€鍖栧鍜屼慨姝ｆ枃鏈?

            expression_details = ai_correction.get('鏂囬噰涓庤〃杈惧垎鏋?, {})

            if not isinstance(expression_details, dict):

                expression_details = {}

                

        except Exception as e:

            print(f"瑙ｆ瀽JSON鎴栨彁鍙栨暟鎹嚭閿? {e}")

            # 璁剧疆榛樿鍊?

            total_score = 0

            level = 'C'

            content_score = 0

            language_score = 0

            structure_score = 0

            writing_score = 0

            errors = []

            strengths = []

            weaknesses = []

            suggestions = []

            comments = "AI璇勫垎绯荤粺鏆傛椂涓嶅彲鐢熼敊璇?
"
            expression_details = {}

            

        # 甯歌閿欏埆瀛楁槧灏勮〃 - 鎻愬墠瀹氫箟鍦ㄥ嚱鏁板紑濮嬪鍜屼慨姝ｆ枃鏈?

        common_corrections = {

            '绐佽笍濂?: '绐佸劧濂旀秾',

            '鎰熶笌瀹夐様': '鎰熶笌瀹夋叞',

            '杩涜交': '杞昏交',

            '杞婚グ': '杞绘嫮',

            '鍫傜潃': '韬虹潃',

            '鐪嬬渷': '鐪嬬湅',

            '浠挎媯': '浠夸經',

            '鏄熸槸': '鏄熻景',

            '婕斿浜嗕竴': '濂忓搷浜嗕竴',

            '鑷冲埌': '鐩村埌',

            # 鍏朵粬甯歌閿欏埆瀛?

            '鐩ぇ': '澶уぇ',

            # 鏂板閿欏埆瀛楁槧灏?

            '绗竴': '娑熸吉',

            '绗簩': '鐣ュ甫',

            '绐佽笍濂?: '绐佺劧濂旀秾',

            '鎰熸叏': '鎰熸叏',

            '绗笁': '灏濊瘯',

            '鏈夎皧': '鍙嬭皧',

            '鏈€鍚庝竴': '闈㈠',

            '鎭嬫剰': '娑熸吉',

            '娑垫吉': '娑熸吉',

            '璺鐣ュ甫': '鐣ュ甫',

            '甯歌瘯': '灏濊瘯'

        }

        

        # 璁＄畻鏂囩珷瀛楁暟锛堜腑鑻辨枃锛?

        if essay:

            # 璁＄畻涓枃瀛楃

            chinese_chars = sum(1 for char in essay if '\u4e00' <= char <= '\u9fff')

            # 璁＄畻鑻辨枃鍗曡瘝鏁帮紙绠€鍗曡绠楋紝浠ョ┖鏍煎垎闅旓級

            english_words = len([word for word in essay.split() if all(c.isalpha() for c in word)])

            # 鎬诲瓧鏁颁负涓枃瀛楃鍔犺嫳鏂囧崟璇嶆暟

            word_count = chinese_chars + english_words

        else:

            word_count = 0

        

        # 妫€鏌ユ枃绔犳槸鍚﹀お鐭?

        if len(essay) < 50:

            return {

                "success": False,

                "error": "鏂囩珷鍐呭闇€瑕佽嚦灏?0涓瓧绗︽墠鑳借繘琛屾壒鏀?,
"
                "score": "鏃犳硶璇勫垎",

                "score_display": "鏃犳硶璇勫垎",

                "score_value": 0,

                "comments": "鏂囩珷鍐呭闇€瑕佽嚦灏?0涓瓧绗︽墠鑳借繘琛屾壒鏀?,
"
                "words_count": word_count

            }

        

        # 浣跨敤Deepseek AI杩涜鎵规敼

        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")

            # 鍑嗗鎵规敼鎻愮ず

            prompt = f"""
"
            根据以下作文进行评价与打分：



            作文题目：{title}

            作文内容：

            {essay}



            字数要求：不少于{MIN_CHARS}字。当前字数：{word_count}字。



            评分标准参考广东中学语文考试：

            总分50分制。给定等级(A/B/C/D)，A为优秀(40-50分)，B为良好(30-39分)，C为及格(20-29分)，D为不及格(0-19分)。



            必须以JSON格式返回结果，结构如下：

            {{

            "总得分": "45",

            "等级评定": "A-优秀",

            "分项得分": {{

                "内容主旨": "22",

                "语言文采": "17",

                "文章结构": "8.5",

                "文面书写": "4.5"

            }},

            "总体评价": ""

            }}

            """
"
            

            print("姝ｅ湪璋冪敤Deepseek AI杩涜鎵规敼...")

            

            # 璋冪敤llm_func.py涓殑model鍑芥暟鑾峰彇Deepseek璇勫垎缁撴灉

            start_time = time.time()  # 璁板綍API璋冪敤寮€濮嬫椂闂?

            response = await model([
)
                {"role": "system", "content": "浣犳槸涓€浣嶄笓涓氱殑涓璇枃鏁欏笀锛屾搮闀块珮鏁堣瘎鍒ゅ鐢熶綔鏂囥€傝鎻愪緵绠€鏄庢壖瑕佺殑鍒嗘瀽锛岄噸鐐圭獊鍑鸿瘎鍒嗗拰涓昏緫
"
            ])

            

            api_time = time.time() - start_time  # 璁＄畻API璋冪敤鑰楁椂

            print(f"Deepseek API璋冪敤鑰楁椂: {api_time:.2f}绉?)
"
            

            if not response or not response.choices:

                raise Exception("Deepseek API杩斿洖缁撴灉涓虹┖")

                

            # 浠巖esponse瀵硅薄涓纭彁鍙栨枃鏈唴瀹?

            response_text = response.choices[0].message.content

            print("Deepseek鎵规敼缁撴灉:", response_text[:200] + "...")

            

            # 灏濊瘯瑙ｆ瀽JSON鍝嶅簲

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                # 灏濊瘯鎻愬彇JSON閮ㄥ垎锛堝鏋滆繑鍥炵殑涓嶆槸绾疛SON锛?

                json_start = response_text.find('{')

                json_end = response_text.rfind('}') + 1

                

                start_parse_time = time.time()  # 璁板綍瑙ｆ瀽寮€濮嬫椂闂?

                

                if json_start >= 0 and json_end > json_start:

                    json_text = response_text[json_start:json_end]

                    ai_correction = json.loads(json_text)

                else:

                    # 濡傛灉娌℃湁鎵惧埌JSON锛屽皾璇曠洿鎺ヨВ鏋愭暣涓搷搴?

                    ai_correction = json.loads(response_text)

                

                parse_time = time.time() - start_parse_time  # 璁＄畻瑙ｆ瀽鑰楁椂

                print(f"JSON瑙ｆ瀽鑰楁椂: {parse_time:.2f}绉?)
"
                

                print("Deepseek鎵规敼缁撴灉瑙ｆ瀽鎴愬姛")

                

                # 瀹夊叏鍦版彁鍙栧垎鏁板拰璇勫畾锛岄伩鍏嶆牸寮忓寲闂

                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")

                    # 鎻愬彇鎬诲垎

                    total_score = 0

                    if '鎬诲緱鍒? in ai_correction:

                        total_score_value = ai_correction['鎬诲緱鍒?]

                        if isinstance(total_score_value, str):

                            total_score = int(total_score_value.strip())

                        else:

                            total_score = int(total_score_value)

                    

                    # 鎻愬彇绛夌骇

                    level = 'C'

                    if '绛夌骇璇勫畾' in ai_correction:

                        level = ai_correction['绛夌骇璇勫畾']

                        if '-' in level:

                            level = level.split('-')[0]

                    

                    # 瀹夊叏澶勭悊鍒嗛」寰楀垎

                    content_score = 0

                    language_score = 0

                    structure_score = 0

                    writing_score = 0

                    

                    if '鍒嗛」寰楀垎' in ai_correction and isinstance(ai_correction['鍒嗛」寰楀垎'], dict):

                        鍒嗛」寰楀垎 = ai_correction['鍒嗛」寰楀垎']

                        

                        # 鍐呭涓绘棬寰楀垎

                        if '鍐呭涓绘棬' in 鍒嗛」寰楀垎:

                            content_value = 鍒嗛」寰楀垎['鍐呭涓绘棬']

                            if isinstance(content_value, str):

                                try:
                                    pass  # 自动修复的空块
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")

                                    content_score = float(content_value.strip())

                                except:

                                    content_score = 0

                            else:

                                content_score = float(content_value)

                        

                        # 璇繡█鏂囬噰寰楀垎

                        if '璇繡█鏂囬噰' in 鍒嗛」寰楀垎:

                            language_value = 鍒嗛」寰楀垎['璇繡█鏂囬噰']

                            if isinstance(language_value, str):

                                try:
                                    pass  # 自动修复的空块
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")

                                    language_score = float(language_value.strip())

                                except:

                                    language_score = 0

                            else:

                                language_score = float(language_value)

                        

                        # 鏂囩珷缁撴瀯寰楀垎

                        if '鏂囩珷缁撴瀯' in 鍒嗛」寰楀垎:

                            structure_value = 鍒嗛」寰楀垎['鏂囩珷缁撴瀯']

                            if isinstance(structure_value, str):

                                try:
                                    pass  # 自动修复的空块
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")

                                    structure_score = float(structure_value.strip())

                                except:

                                    structure_score = 0

                            else:

                                structure_score = float(structure_value)

                        

                        # 鏂囬潰涔﹀啓寰楀垎

                        if '鏂囬潰涔﹀啓' in 鍒嗛」寰楀垎:

                            writing_value = 鍒嗛」寰楀垎['鏂囬潰涔﹀啓']

                            if isinstance(writing_value, str):

                                try:
                                    pass  # 自动修复的空块
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")
                                except Exception as e:
                                    logger.error(f"发生错误: {str(e)}")

                                    writing_score = float(writing_value.strip())

                                except:

                                    writing_score = 0

                            else:

                                writing_score = float(writing_value)

                except Exception as extract_error:

                    print(f"鎻愬彇寰楀垎鏁版嵁鍑洪敊: {extract_error}")

                    # 璁剧疆榛樿鍊?

                    total_score = 35

                    level = 'C'

                    content_score = 8.0

                    language_score = 7.0

                    structure_score = 7.0

                    writing_score = 4.0

                

                # 閿欏埆瀛楀垎鏋?- 浼樺寲澶勭悊閫昏緫

                errors = []

                if '閿欏埆瀛楀垎鏋? in ai_correction and isinstance(ai_correction['閿欏埆瀛楀垎鏋?], list):

                    # 鎻愬彇閿欏埆瀛楀垎鏋愰噷鐨勫垪琛ㄥ唴瀹?

                    error_list = ai_correction['閿欏埆瀛楀垎鏋?]

                    

                    # 濡傛灉鎵ｅ垎椤逛腑鏈夊祵濂楃粨鏋?

                    if '鎵ｅ垎椤? in ai_correction and isinstance(ai_correction['鎵ｅ垎椤?], dict) and '閿欏埆瀛楀垎鏋? in ai_correction['鎵ｅ垎椤?]:

                        if isinstance(ai_correction['鎵ｅ垎椤?]['閿欏埆瀛楀垎鏋?], list):

                            error_list = ai_correction['鎵ｅ垎椤?]['閿欏埆瀛楀垎鏋?]

                    

                    # 鍙鐞嗗墠5涓敊鍒瓧锛岄伩鍏嶈繃澶氬鐞?

                    for error in error_list[:5]:

                        if isinstance(error, dict):

                            # 鑾峰彇閿欒鍜屼慨姝ｆ枃鏈?

                            error_text = error.get('閿欒鍜屼慨姝ｆ枃鏈?, '')

                            position_text = error.get('浣嶇疆', '')

                            correction_text = error.get('淇', error.get('姝ｇ'鍐欐硶', ''))

                            context = error.get('涓婁笅鏂?, '')

                            

                            # 濡傛灉娌℃湁涓婁笅鏂囦絾鏈変綅缃俊鎭紝鍙互浣跨敤浣嶇疆浣滀负涓婁笅鏂?

                            if not context and position_text:

                                context = position_text

                                

                            # 纭繚鏈夋湁鏁堢殑閿欏埆瀛椾俊鎭?

                            if error_text and correction_text:

                                err_obj = {

                                    "error": error_text,

                                    "correction": correction_text,

                                    "position": position_text,

                                    "context": context

                                }

                                errors.append(err_obj)

                

                # 浼樼己鐐逛笌寤鸿 - 绠€鍖栧鍜屼慨姝ｆ枃鏈?

                strengths = ai_correction.get('浣滄枃浼樼偣', [])

                if not isinstance(strengths, list):

                    strengths = [strengths] if strengths else []

                

                weaknesses = ai_correction.get('浣滄枃涓嶈冻', [])

                if not isinstance(weaknesses, list):

                    weaknesses = [weaknesses] if weaknesses else []

                

                suggestions = ai_correction.get('鏀硅繘寤鸿', [])

                if not isinstance(suggestions, list):

                    suggestions = [suggestions] if suggestions else []

                

                comments = ai_correction.get('鎬讳綋璇勪环', '')

                

                # 鎻愬彇琛ㄨ揪鏂囬噰鍒嗘瀽 - 绠€鍖栧鍜屼慨姝ｆ枃鏈?

                expression_details = ai_correction.get('鏂囬噰涓庤〃杈惧垎鏋?, {})

                if not isinstance(expression_details, dict):

                    expression_details = {}

                

                sentence_style = expression_details.get('鍙ュ紡鍒嗘瀽', "鍙ュ紡鍒嗘瀽鏁版嵁鏈彁渚?)                
"
                word_choice = expression_details.get('鐢ㄨ瘝鍒嗘瀽', "鐢ㄨ瘝鍒嗘瀽鏁版嵁鏈彁渚?)
"
                transition = expression_details.get('杩囨浮琛旀帴', "杩囨浮琛旀帴鍒嗘瀽鏁版嵁鏈彁渚?)
"
                rhetoric = expression_details.get('淇緸鎵嬫硶', "淇緸鎵嬫硶鍒嗘瀽鏁版嵁鏈彁渚?)
"
                

                total_time = time.time() - start_time  # 璁＄畻鎬诲鐞嗘椂闂?

                print(f"鎵规敼鎬昏€楁椂: {total_time:.2f}绉?)
"
                

                # 杩斿洖鎵规敼缁撴灉

                return {

                    "success": True,

                    "score": str(total_score),

                    "score_display": str(total_score),

                    "score_value": int(total_score),

                    "level": level,

                    "total_score": float(total_score) / 10,  # 杞负灏忔暟浠ュ吋瀹瑰墠绔樉绀洪€昏緫

                    "content_score": float(content_score),

                    "language_score": float(language_score),

                    "structure_score": float(structure_score),

                    "writing_score": float(writing_score),

                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),

                    "process_time": f"{total_time:.1f}绉?,
"
                    "errors": errors if errors else [{"error": "鏈彂鐜伴敊鍒瓧", "correction": "鏃犻渶淇", "position": "", "context": ""}],

                    "error_count": len(errors),

                    "comments": comments if comments else "鎬讳綋鏉ヨ锛岃繖鏄竴绡囦笉閿欑殑鏂囩珷锛屾湁涓瀹氱殑琛ㄨ揪鑳藉姏",

                    "strengths": strengths if strengths else ["鍐呭绗﹀悎棰樻剰", "缁撴瀯娓呮櫚", "璇繡█娴佺晠"],

                    "weaknesses": weaknesses if weaknesses else ["鍙互澧炲姞涓浜涚粏鑺傛弿鍐?, "鏂囩珷娣卞害鏈夊緟鍔犲己"],
"
                    "suggestions": suggestions if suggestions else ["寤鸿涓板瘜缁嗚妭鎻忓啓", "鍙互澧炲姞涓浜敓鍔ㄧ殑姣斿柣"],

                    "words_count": word_count,

                    "content_analysis": ai_correction.get('鍐呭鍒嗘瀽', {
)
                        "涓婚": "鍒囧悎棰樻剰锛屼腑蹇冩槑纭?,
"
                        "鍐呭": "鍐呭鍏蜂綋锛屼絾鍙互杩涗竴姝ヤ赴瀵岀粏鑺?,
"
                        "缁撴瀯": "缁撴瀯瀹屾暣锛屽眰娆"垎鏄?,

                        "绔嬫剰": strengths[0] if strengths else "绔嬫剰鏄庣'锛屼腑蹇冪獊鍑?
"
                    }),

                    "expression_analysis": {

                        "strengths": ["璇繡█琛ㄨ揪娴佺晠鑷劧", "閮ㄥ垎琛ㄨ揪鑷劧寰椾綋"],

                        "weaknesses": ["璇嶆眹鍗曚竴锛氱敤璇嶈櫧鐒跺噯纭, "鍙ュ紡绠€鍗曪細鍙ュ紡缁撴瀯杈冧负鍗曚竴锛屽缓璁鍔犻暱鍙ャ€佸鍚堝彞绛夊鏍峰寲鍙ュ紡", "杩囨浮鐢熺‖锛氶儴鍒嗘鍚堝彞绛夊鏍峰寲鍙ュ紡", "杩囨浮鐢熺‖锛氶儴鍒嗘鍚堝彞绛夊鏍峰寲鍙ュ紡"],
"
                        "sentence_style": sentence_style,

                        "word_choice": word_choice,

                        "transition": transition,

                        "rhetoric": rhetoric

                    }

                }

            except json.JSONDecodeError as e:

                print(f"JSON瑙ｆ瀽閿欒: {e}")

                print(f"鍘熷鍝嶅簲鍐呭: {response_text[:200]}...")

                

                # 灏濊瘯鎻愬彇鍏抽敭淇℃伅鐨勭畝鍖栫増鏈?

                # 浠庢枃鏈鍒嗘暟

                score_match = re.search(r'鎬诲緱鍒哰:锛歖\s*(\d+)', response_text)

                total_score = int(score_match.group(1)) if score_match else 35

                

                # 灏濊瘯鎻愬彇璇勭骇

                level_match = re.search(r'绛夌骇璇勫畾[:锛歖\s*([ABCD])', response_text)

                level = level_match.group(1) if level_match else 'C'

                

                # 浠庡師濮嬫枃鏈鍒嗘暟

                return {

                    "success": True,

                    "score": str(total_score),

                    "score_display": str(total_score),

                    "score_value": int(total_score),

                    "level": level,

                    "total_score": float(total_score) / 10,

                    "content_score": 8.0,  # 榛樿鍒嗘暟

                    "language_score": 7.0,

                    "structure_score": 7.0, 

                    "writing_score": 4.0,

                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),

                    "process_time": f"{time.time() - start_time:.1f}绉?,
"
                    "errors": [],

                    "error_count": 0,

                    "comments": "绯荤粺瑙ｆ瀽缁撴灉鍑洪敊锛屼絾浠嶆彁渚涗簡鍩烘湰璇勫垎銆傝繖鏄竴绡囦笉閿欑殑鏂囩珷锛屾湁涓瀹氱殑琛ㄨ揪鑳藉姏",

                    "strengths": ["鍐呭绗﹀悎棰樻剰", "缁撴瀯鍩烘湰娓呮櫚"],

                    "weaknesses": ["琛ㄨ揪鍙互杩涗竴姝ユ彁鍗?", "闇€瑕佹彁鍗囪〃杈剧簿纭"],

                    "suggestions": ["寤鸿浼樺寲璇繡█琛ㄨ揪", "娣卞寲鏂囩珷涓婚"],

                    "words_count": word_count,

                    "content_analysis": {"涓婚": "鍩烘湰绗﹀悎棰樻剰"},

                    "expression_analysis": {

                        "strengths": ["鍩烘湰璇繡█琛ㄨ揪鑳藉姏"],

                        "weaknesses": ["闇€瑕佹彁鍗囪〃杈剧簿纭"],

                        "sentence_style": "鍙ュ紡鍒嗘瀽澶辫触",

                        "word_choice": "鐢ㄨ瘝鍒嗘瀽澶辫触",

                        "transition": "杩囨浮琛旀帴鍒嗘瀽澶辫触",

                        "rhetoric": "淇緸鎵嬫硶鍒嗘瀽澶辫触"

                    }

                }

        except Exception as api_error:

            error_msg = str(api_error)

            with open("error.log", "a", encoding="utf-8") as f:

                f.write(f"{datetime.datetime.now()} - 鎵规敼閿欒: {error_msg}\n")

                if 'response_text' in locals():

                    f.write(f"鍝嶅簲鍐呭: {response_text[:200]}\n")

                f.write("-" * 50 + "\n")

            print(f"Deepseek AI鍑洪敊: {error_msg}")

            

            # 鐩存帴杩斿洖閿欒鎻愮ず锛屼笉浣跨敤澶囩敤妯℃嫙鎵规敼

            return {

                "success": False,

                "error": f"AI鍑洪敊: {str(api_error)}",

                "score": "鏃犳硶璇勫垎",

                "score_display": "鏃犳硶璇勫垎", 

                "score_value": 0,

                "level": "鏃犳硶璇勫畾",

                "total_score": 0.0,

                "content_score": 0.0,

                "language_score": 0.0,

                "structure_score": 0.0,

                "writing_score": 0.0,

                "comments": "AI璇勫垎绯荤粺鏆傛椂鏃犳硶浣跨敤锛岃繖鏄竴绡囦笉閿欑殑鏂囩珷锛屾湁涓瀹氱殑琛ㄨ揪鑳藉姏",

                "words_count": word_count,

                "errors": [],

                "error_count": 0,

                "strengths": ["璇烽噸鏂版彁浜や綔鏂囪繘琛屾壒鏀?],
"
                "weaknesses": ["绯荤粺鏆傛椂鏃犳硶杩涜鍐呭鍒嗘瀽"],

                "suggestions": ["璇锋鏌ョ綉缁滆繛鎺ュ苟绋嶅悗鍐嶈瘯"],

                "content_analysis": {

                    "鐘舵€?: "AI璇勫垎绯荤粺鏆傛椂鏃犳硶杩炴帴锛岃繖鏄竴绡囦笉閿欑殑鏂囩珷锛屾湁涓瀹氱殑琛ㄨ揪鑳藉姏銆?

                },

                "expression_analysis": {

                    "strengths": ["璇烽噸鏂版彁浜や綔鏂囪繘琛屾壒鏀?],
"
                    "weaknesses": ["绯荤粺鏆傛椂鏃犳硶杩涜鍐呭鍒嗘瀽"],

                    "sentence_style": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽鍙ュ紡",

                    "word_choice": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽鐢ㄨ瘝",

                    "transition": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽杩囨浮琛旀帴",

                    "rhetoric": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽淇緸鎵嬫硶"

                }

            }

    except Exception as e:

        import traceback

        error_type = type(e).__name__

        error_msg = str(e)

        trace = traceback.format_exc()

        print(f"鎵规敼杩囩▼涓嚭閿欑被鍨? {error_type}")

        print(f"鎵规敼杩囩▼涓嚭閿? {error_msg}")

        print(f"閿欒杩芥函: {trace}")

        return {

            "success": False,

            "error": f"鎵规敼杩囩▼涓嚭閿?{str(e)}",

            "score": "鏃犳硶璇勫垎",

            "score_display": "鏃犳硶璇勫垎", 

            "score_value": 0,

            "level": "鏃犳硶璇勫畾",

            "total_score": 0.0,

            "content_score": 0.0,

            "language_score": 0.0,

            "structure_score": 0.0,

            "writing_score": 0.0,

            "words_count": word_count if 'word_count' in locals() else (len(essay) if essay else 0),

            "errors": [],

            "error_count": 0,

            "strengths": ["璇烽噸鏂版彁浜や綔鏂囪繘琛屾壒鏀?],
"
            "weaknesses": ["绯荤粺鏆傛椂鏃犳硶杩涜鍐呭鍒嗘瀽"],

            "suggestions": ["璇锋鏌ユ偍鐨勪綔鏂囧唴瀹瑰苟绋嶅悗鍐嶈瘯"],

            "content_analysis": {

                "鐘舵€?: "绯荤粺澶勭悊杩囩▼涓嚭閿欙紝璇风◢鍚庡啀璇曘€?

            },

            "expression_analysis": {

                "strengths": ["璇烽噸鏂版彁浜や綔鏂囪繘琛屾壒鏀?],
"
                "weaknesses": ["绯荤粺鏆傛椂鏃犳硶杩涜鍐呭鍒嗘瀽"],

                "sentence_style": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽鍙ュ紡",

                "word_choice": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽鐢ㄨ瘝",

                "transition": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽杩囨浮琛旀帴",

                "rhetoric": "绯荤粺鏆傛椂鏃犳硶鍒嗘瀽淇緸鎵嬫硶"

            }

        }



# 鏂囦欢澶勭悊鍑芥暟

def extract_text_from_docx(file_path):

    """浠嶹ord鏂囨。涓彁鍙栨枃鏈?""
"
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        print(f"寮€濮嬪鐞嗘枃浠?{file_path}")

        file_ext = os.path.splitext(file_path)[1].lower()

        

        # 娣诲姞debug鏃ュ織

        print(f"鏂囦欢鎵╁睍鍚?{file_ext}")

        print(f"鏂囦欢澶у皬: {os.path.getsize(file_path)} 瀛楄妭")

        

        if file_ext == '.doc':

            print("妫€娴嬪埌.doc鏂囦欢锛屽皾璇曞鐞?..")

            

            # 灏濊瘯浣跨敤antiword锛堝鏋滃凡瀹夎鏂囦欢

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                import subprocess

                print("灏濊瘯浣跨敤antiword澶勭悊.doc鏂囦欢")

                # 鍒涘缓涓存椂鏂囨湰鏂囦欢

                temp_txt = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)

                temp_txt_path = temp_txt.name

                temp_txt.close()

                

                # 浣跨敤antiword鍛戒护锛堥渶瑕侀鍏堝畨瑁咃級

                result = subprocess.run(['antiword', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode == 0 and result.stdout:

                    print("鎴愬姛浣跨敤antiword鎻愬彇鏂囨湰")

                    return result.stdout

            except Exception as e:

                print(f"antiword澶勭悊澶辫触: {e}")

            

            # 灏濊瘯浣跨敤textract锛堝鏋滃凡瀹夎鏂囦欢

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                import textract

                print("灏濊瘯浣跨敤textract澶勭悊.doc鏂囦欢")

                text = textract.process(file_path).decode('utf-8')

                if text and len(text) > 10:

                    print("鎴愬姛浣跨敤textract鎻愬彇鏂囨湰")

                    return text

            except Exception as e:

                print(f"textract澶勭悊澶辫触: {e}")

            

            # 灏濊瘯鐩存帴浣跨敤docx2txt澶勭悊锛堝敖绠"畠閫氬父涓嶆敮鎸乨oc锛?
"
            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                print("灏濊瘯浣跨敤docx2txt鐩存帴澶勭悊.doc鏂囦欢")

                text = docx2txt.process(file_path)

                if text and len(text) > 10:  # 纭繚鎻愬彇鍒颁簡鏈夋剰涔夌殑鍐呭

                    return text

            except Exception as docx2txt_error:

                print(f"docx2txt澶勭悊.doc鏂囦欢澶辫触: {docx2txt_error}")

            

            # 灏濊瘯浣跨敤鏂囦欢閲嶅懡鍚嶆妧宸у鐞哾oc鏂囦欢

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                print("灏濊瘯浣跨敤鏂囦欢閲嶅懡鍚嶆柟娉曞鐞?doc鏂囦欢")

                # 鍒涘缓涓€涓复鏃剁殑.docx鏂囦欢

                temp_docx = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)

                temp_docx_path = temp_docx.name

                temp_docx.close()

                

                # 澶嶅埗.doc鏂囦欢鍐呭鍒癲ocx鏂囦欢

                with open(file_path, 'rb') as src:

                    with open(temp_docx_path, 'wb') as dst:

                        dst.write(src.read())

                

                # 灏濊瘯鐢╠ocx2txt澶勭悊杩欎釜"涓存椂.docx鏂囦欢
"
                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")

                    text = docx2txt.process(temp_docx_path)

                    if text and len(text) > 10:

                        print("浣跨敤涓存椂鏂规硶鎴愬姛鎻愬彇鏂囨湰")

                        os.unlink(temp_docx_path)  # 鍒犻櫎涓存椂鏂囦欢

                        return text

                except:

                    pass

                

                # 娓呯悊涓存椂鏂囦欢

                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")

                    os.unlink(temp_docx_path)

                except:

                    pass

            except Exception as rename_error:

                print(f"鏂囦欢閲嶅懡鍚嶆柟娉曞け璐?{rename_error}")

            

            # 濡傛灉浠ヤ笂鏂规硶閮藉け璐ワ紝浣跨敤绯荤粺鍛戒护灏濊瘯杞崲鏂囦欢

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                print("灏濊瘯浣跨敤绯荤粺鍛戒护杞崲鏂囦欢")

                if os.name == 'nt':  # Windows

                    # 浣跨敤PowerShell灏濊瘯杞崲

                    import subprocess

                    temp_txt = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)

                    temp_txt_path = temp_txt.name

                    temp_txt.close()

                    

                    # PowerShell鍛戒护灏濊瘯璇诲彇Word鏂囨。

                    ps_command = f'''

                    Add-Type -AssemblyName "Microsoft.Office.Interop.Word"

                    $word = New-Object -ComObject Word.Application

                    $word.Visible = $false

                    $doc = $word.Documents.Open("{file_path}")

                    $text = $doc.Content.Text

                    $doc.Close()

                    $word.Quit()

                    Set-Content -Path "{temp_txt_path}" -Value $text

                    '''

                    

                    # 鍒涘缓涓存椂PowerShell鑴氭湰

                    ps_script = tempfile.NamedTemporaryFile(suffix='.ps1', delete=False)

                    ps_script_path = ps_script.name

                    ps_script.close()

                    

                    with open(ps_script_path, 'w', encoding='utf-8') as f:

                        f.write(ps_command)

                    

                    # 鎵цPowerShell鑴氭湰

                    subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', ps_script_path])

                    

                    # 璇诲彇缁撴灉

                    try:
                        pass  # 自动修复的空块
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")

                        with open(temp_txt_path, 'r', encoding='utf-8') as f:

                            text = f.read()

                            if text and len(text) > 10:

                                print("浣跨敤PowerShell鎴愬姛鎻愬彇鏂囨湰")

                                # 娓呯悊涓存椂鏂囦欢

                                os.unlink(ps_script_path)

                                os.unlink(temp_txt_path)

                                return text

                    except Exception as e:

                        print(f"璇诲彇PowerShell缁撴灉澶辫触: {e}")

                    

                    # 娓呯悊涓存椂鏂囦欢

                    os.unlink(ps_script_path)

                    os.unlink(temp_txt_path)

            except Exception as system_error:

                print(f"绯荤粺鍛戒护杞崲澶辫触: {system_error}")

            

            # 濡傛灉鎵€鏈夋柟娉曢兘澶辫触锛屾樉绀哄弸濂界殑閿欒鍜屼慨姝ｆ枃鏈?

            return "鏃犳硶璇诲彇.doc鏂囦欢锛岃灏嗘枃浠惰浆鎹负.docx鏍煎紡鎴栬€呬娇鐢ㄦ枃鏈鐩存帴绮樿创浣滄枃鍐呭"

        else:

            # 浣跨敤澶氱鏂规硶澶勭悊.docx鏂囦欢

            print("妫€娴嬪埌.docx鏂囦欢锛屽皾璇曞鐞?..")

            

            # 鏂规硶1: 浣跨敤docx2txt鐩存帴澶勭悊

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                print("灏濊瘯浣跨敤docx2txt澶勭悊.docx鏂囦欢")

                text = docx2txt.process(file_path)

                if text and len(text) > 10:

                    print(f"浣跨敤docx2txt鎴愬姛鎻愬彇鏂囨湰锛岄暱搴?{len(text)}")

                    print(f"鏂囨湰棰勮: {text[:100]}...")

                    return text

                else:

                    print("docx2txt鎻愬彇鐨勬枃鏈お鐭垨涓虹┖")

            except Exception as e:

                print(f"docx2txt澶勭悊澶辫触: {e}")

            

            # 鏂规硶2: 浣跨敤python-docx搴?

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                print("灏濊瘯浣跨敤python-docx搴撳鐞?docx鏂囦欢")

                import docx

                doc = docx.Document(file_path)

                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

                if text and len(text) > 10:

                    print(f"浣跨敤python-docx鎴愬姛鎻愬彇鏂囨湰锛岄暱搴?{len(text)}")

                    print(f"鏂囨湰棰勮: {text[:100]}...")

                    return text

                else:

                    print("python-docx鎻愬彇鐨勬枃鏈お鐭垨涓虹┖")

            except Exception as e:

                print(f"python-docx澶勭悊澶辫触: {e}")

            

            # 鏂规硶3: 灏濊瘯鐩存帴璇诲彇xml鍐呭

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                print("灏濊瘯閫氳繃瑙ｅ帇.docx鏂囦欢鎻愬彇鏂囨湰")

                import zipfile

                import re

                

                text = ""

                # .docx鏂囦欢瀹為檯涓婃槸zip鏂囦欢锛屽寘鍚玾ord/document.xml

                with zipfile.ZipFile(file_path) as docx_zip:

                    content = docx_zip.read('word/document.xml').decode('utf-8')

                    # 鎻愬彇鏂囨湰鍐呭

                    text = re.sub(r'<[^>]+>', '', content)

                    text = re.sub(r'\s+', ' ', text).strip()

                

                if text and len(text) > 10:

                    print(f"閫氳繃瑙ｅ帇XML鎴愬姛鎻愬彇鏂囨湰锛岄暱搴?{len(text)}")

                    print(f"鏂囨湰棰勮: {text[:100]}...")

                    return text

                else:

                    print("XML鎻愬彇鐨勬枃鏈お鐭垨涓虹┖")

            except Exception as e:

                print(f"XML鎻愬彇澶勭悊澶辫触: {e}")

            

            # 濡傛灉鎵€鏈夋柟娉曢兘澶辫触锛岃繑鍥炲弸濂界殑閿欒鍜屼慨姝ｆ枃鏈?

            print("鎵€鏈夋枃鏈彁鍙栨柟娉曞潎澶辫触")

            return "鏈兘鎴愬姛浠嶹ord鏂囨。涓彁鍙栨枃鏈紝璇峰皾璇曞皢鏂囦欢杞负.txt鏍煎紡鎴栫洿鎺ュ鍒舵枃鏈埌杈撳叆妗嗕腑"

    except Exception as e:

        print(f"浠嶹ord鏂囨。涓彁鍙栨枃鏈嚭閿?{e}")

        return "澶勭悊鏂囨。鏃堕亣鍒伴敊璇紝璇峰皾璇曞叾浠栨牸寮忔垨鐩存帴绮樿创鍐呭"



def extract_text_from_pdf(file_path):

    """浠嶱DF鏂囦欢涓彁鍙栨枃鏈唴瀹?""
"
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        # 浣跨敤PyPDF2鎻愬彇鏂囨湰

        with open(file_path, 'rb') as file:

            pdf_reader = PyPDF2.PdfReader(file)

            text = ''

            for page_num in range(len(pdf_reader.pages)):

                text += pdf_reader.pages[page_num].extract_text() or ''

            

            # 濡傛灉鎻愬彇鐨勬枃鏈緢灏戯紝鍙兘鏄壂鎻忓瀷PDF锛屽皾璇曚娇鐢∣CR

            if len(text.strip()) < 100:

                print("PDF鏂囨湰鍐呭寰堝皯锛屽彲鑳芥槸鎵弿鍨婸DF锛屽皾璇昈CR澶勭悊...")

                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")

                    # 璁剧疆Poppler璺緞

                    poppler_path = os.path.join(os.getcwd(), 'poppler', 'Library', 'bin')

                    if os.path.exists(poppler_path):

                        # 灏哖DF杞崲涓哄浘鍍?

                        images = convert_from_path(file_path, dpi=300, poppler_path=poppler_path)

                        

                        # 瀵规瘡涓浘鍍忚繘琛孫CR

                        ocr_service = OcrService()

                        all_text = []

                        

                        for i, image in enumerate(images):

                            # 淇濆瓨涓轰复鏃跺浘鍍忔枃浠?

                            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')

                            image.save(temp_img.name, 'JPEG')

                            temp_img.close()

                            

                            # 浣跨敤OCR鎻愬彇鏂囨湰

                            page_text = ocr_service.process_image(temp_img.name, method="qwen")["text"]

                            all_text.append(page_text)

                            

                            # 鍒犻櫎涓存椂鍥惧儚鏂囦欢

                            try:
                                pass  # 自动修复的空块
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")

                                os.unlink(temp_img.name)

                            except:

                                pass

                                

                        # 鍚堝苟鎵€鏈夐〉闈㈢殑鏂囨湰

                        text = '\n\n'.join(all_text)

                    else:

                        print(f"鎵句笉鍒癙oppler璺緞: {poppler_path}")

                        raise Exception(f"鎵句笉鍒癙oppler璺緞: {poppler_path}")

                except Exception as e:

                    print(f"PDF OCR澶勭悊鍑洪敊: {str(e)}")

                    raise Exception(f"鏃犳硶浠嶱DF涓彁鍙栨枃鏈?{str(e)}")

                    

        return text.strip()

    except Exception as e:

        print(f"浠嶱DF鏂囦欢涓彁鍙栨枃鏈嚭閿?{str(e)}")

        raise Exception(f"浠嶱DF鏂囦欢涓彁鍙栨枃鏈嚭閿?{str(e)}")



def extract_text_from_image(file_path):

    """浠庡浘鐗囦腑鎻愬彇鏂囨湰锛堜娇鐢∣CR锛?""
"
    temp_jpeg_path = None

    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        print(f"寮€濮婳CR澶勭悊鍥剧墖: {file_path}")

        

        # 浣跨敤鏂扮殑OCR鏈嶅姟澶勭悊鍥惧儚

        ocr_result = ocr_service.process_image(file_path, method=OCR_PROVIDER)

        

        if ocr_result["success"]:

            print(f"OCR澶勭悊鎴愬姛 (浣跨敤{ocr_result['method']}鏂规硶), 鏂囨湰闀垮害: {len(ocr_result['text'])}")

            return ocr_result["text"]

        else:

            # OCR澶辫触锛屾姏鍑哄紓甯?

            error_msg = ocr_result.get("error", "鏈煡OCR閿欒鍜屼慨姝ｆ枃鏈?")

            print(f"OCR澶勭悊澶辫触: {error_msg}")

            raise Exception(f"OCR澶勭悊澶辫触: {error_msg}")

                

    except Exception as e:               

        print(f"浠庡浘鐗囦腑鎻愬彇鏂囨湰鍑洪敊: {e}")

        raise Exception(f"澶勭悊鍥剧墖鏂囦欢鏃跺嚭閿?{e}")



def extract_text_from_image_baidu(file_path):

    """浣跨敤鐧惧害鍗冨竼API杩涜OCR璇嗗埆"""

    if not QIANFAN_AK or not QIANFAN_SK:

        raise Exception("鏈厤缃櫨搴﹀崈甯咥PI瀵嗛挜锛屾棤娉曚娇鐢ㄧ櫨搴I OCR鍔熻兘")

    

    # 鑾峰彇璁块棶浠ょ墝

    token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={QIANFAN_AK}&client_secret={QIANFAN_SK}"

    response = requests.post(token_url)

    if response.status_code != 200:

        raise Exception(f"鑾峰彇鐧惧害鍗冨竼API浠ょ墝澶辫触: {response.text}")

    

    access_token = response.json()["access_token"]

    

    # 鍑嗗鍥剧墖鏁版嵁

    with open(file_path, "rb") as f:

        image_data = base64.b64encode(f.read()).decode("utf-8")

    

    # 璋冪敤閫氱敤鏂囧瓧璇嗗埆API

    ocr_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    data = {"image": image_data}

    

    response = requests.post(ocr_url, headers=headers, data=data)

    if response.status_code != 200:

        raise Exception(f"鐧惧害鍗冨竼OCR API璋冪敤澶辫触: {response.text}")

    

    result = response.json()

    if "error_code" in result:

        raise Exception(f"鐧惧害鍗冨竼OCR API閿欒鍜屼慨姝ｆ枃鏈?: {result}")

    

    # 鎻愬彇璇嗗埆鐨勬枃鏈?

    words_result = result.get("words_result", [])

    text = "\n".join([item["words"] for item in words_result])

    

    return text



def extract_text_from_image_qwen(file_path):

    """浣跨敤闃块噷鍗冮棶-VL妯″瀷杩涜OCR璇嗗埆"""

    if not DASHSCOPE_API_KEY:

        raise Exception("鏈厤缃崈闂瓵PI瀵嗛挜锛屾棤娉曚娇鐢ㄥ崈闂瓵I OCR鍔熻兘")

    

    # 鍑嗗鍥剧墖鏁版嵁

    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        print(f"鍑嗗璇诲彇鍥剧墖鏂囦欢: {file_path}")

        with open(file_path, "rb") as f:

            image_content = f.read()

        

        print(f"鍥剧墖鏂囦欢澶у皬: {len(image_content)/1024:.2f} KB")

        

        # 杞崲鍥剧墖涓篵ase64鏍煎紡

        image_base64 = base64.b64encode(image_content).decode('utf-8')

        print("宸插畬鎴愬浘鐗囪浆Base64缂栫爜")

        

        # 璋冪敤鍗冮棶VL妯″瀷API

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

        headers = {

            "Content-Type": "application/json",

            "Authorization": f"Bearer {DASHSCOPE_API_KEY}"

        }

        

        # 绠€鍖栬姹備綋锛岀洿鎺ヨ姹侽CR

        payload = {

            "model": DASHSCOPE_MODEL,  # 浣跨敤鐜鍙橀噺涓厤缃殑妯″瀷

            "input": {

                "messages": [

                    {

                        "role": "user",

                        "content": [

                            {"image": f"data:image/jpeg;base64,{image_base64}"},

                            {"text": "杩欐槸涓€寮犳枃瀛楀浘鐗囥€傝甯垜璇嗗埆鍥剧墖涓殑鎵€鏈夋枃瀛楀苟鍘熸牱杈撳嚭锛屼笉瑕佹坊鍔犱换浣曡В閲婃垨璇存槑銆?}
"
                        ]

                    }

                ]

            },

            "parameters": {

                "result_format": "message",

                "max_tokens": 2000,

                "temperature": 0.01,

                "top_p": 0.8

            }

        }

        

        # 鍙戦€佽姹傦紝娣诲姞瓒呮椂鍜岄噸璇?

        print(f"璋冪敤鍗冮棶OCR API锛屾ā鍨?{DASHSCOPE_MODEL}")

        print(f"璇锋眰URL: {url}")

        

        # 娣诲姞閲嶈瘯閫昏緫

        max_retries = 3

        retry_delay = 2  # 绉?

        

        for attempt in range(max_retries):

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                print(f"灏濊瘯鍙戦€佽姹?灏濊瘯 {attempt+1}/{max_retries})...")
)
                # 娣诲姞瓒呮椂鍙傛暟

                response = requests.post(url, headers=headers, json=payload, timeout=(15, 180))  # 澧炲姞瓒呮椂鏃堕棿

                print(f"璇锋眰宸插彂閫侊紝鐘舵€佺爜: {response.status_code}")

                

                if response.status_code != 200:

                    print(f"鍗冮棶OCR API璋冪敤澶辫触 (灏濊瘯 {attempt+1}/{max_retries}): 鐘舵€佺爜 {response.status_code}")

                    print(f"閿欒鍜屼慨姝ｆ枃鏈?: {response.text}")

                    

                    if attempt < max_retries - 1:

                        print(f"灏嗗湪 {retry_delay} 绉掑悗閲嶈瘯...")

                        import time

                        time.sleep(retry_delay)

                        retry_delay *= 2  # 鎸囨暟閫€閬?

                        continue

                    else:

                        raise Exception(f"鍗冮棶OCR API璋冪敤澶辫触锛岀姸鎬佺爜: {response.status_code}锛岄敊璇?{response.text}")

                

                result = response.json()

                print("鍗冮棶OCR API璋冪敤鎴愬姛")

                

                # 鎻愬彇鐢熸垚鐨勬枃鏈?

                if 'output' not in result or 'choices' not in result.get('output', {}):

                    print(f"OCR鍝嶅簲鏍煎紡寮傚父: {result}")

                    raise Exception("鍗冮棶OCR鍝嶅簲鏍煎紡寮傚父锛屾湭鑳芥壘鍒拌緭鍑哄唴瀹?)
"
                

                content = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")

                if not content or not content.strip():

                    print("OCR璇嗗埆鏈繑鍥炴枃鏈唴瀹?)
"
                    raise Exception("鍗冮棶OCR鏈繑鍥炴湁鏁堟枃鏈唴瀹?)
"
                    

                print(f"鎴愬姛鎻愬彇OCR鏂囨湰锛岄暱搴?{len(content)}")

                return content

                

            except requests.exceptions.ConnectionError as e:

                print(f"缃戠粶杩炴帴閿欒鍜屼慨姝ｆ枃鏈?: {str(e)}")

                

                if attempt < max_retries - 1:

                    print(f"灏嗗湪 {retry_delay} 绉掑悗閲嶈瘯...")

                    import time

                    time.sleep(retry_delay)

                    retry_delay *= 2  # 鎸囨暟閫€閬?

                else:

                    print("杈惧埌鏈€澶ч噸璇曟鏁帮紝鏀惧純璇锋眰")

                    raise Exception(f"鍗冮棶OCR API璇锋眰杩炴帴閿欒鍜屼慨姝ｆ枃鏈?: {str(e)}")

                    

            except requests.exceptions.Timeout as e:

                print(f"璇锋眰瓒呮椂 (灏濊瘯 {attempt+1}/{max_retries}): {str(e)}")

                

                if attempt < max_retries - 1:

                    print(f"灏嗗湪 {retry_delay} 绉掑悗閲嶈瘯...")

                    import time

                    time.sleep(retry_delay)

                    retry_delay *= 2  # 鎸囨暟閫€閬?

                else:

                    print("杈惧埌鏈€澶ч噸璇曟鏁帮紝鏀惧純璇锋眰")

                    raise Exception(f"鍗冮棶OCR API璇锋眰瓒呮椂: {str(e)}")

                    

            except requests.exceptions.RequestException as e:

                print(f"璇锋眰寮傚父 (灏濊瘯 {attempt+1}/{max_retries}): {str(e)}")

                

                if attempt < max_retries - 1:

                    print(f"灏嗗湪 {retry_delay} 绉掑悗閲嶈瘯...")

                    import time

                    time.sleep(retry_delay)

                    retry_delay *= 2  # 鎸囨暟閫€閬?

                else:

                    print("杈惧埌鏈€澶ч噸璇曟鏁帮紝鏀惧純璇锋眰")

                    raise Exception(f"鍗冮棶OCR API璇锋眰寮傚父: {str(e)}")

    except Exception as e:

        print(f"鍗冮棶OCR澶勭悊杩囩▼涓彂鐢熼敊璇?{str(e)}")

        raise Exception(f"鍗冮棶OCR澶勭悊澶辫触: {str(e)}")



# 娣诲姞TXT鏂囦欢澶勭悊鍑芥暟

def extract_text_from_txt(file_path):

    """浠嶵XT鏂囨湰鏂囦欢涓彁鍙栨枃鏈?""
"
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        # 灏濊瘯浠TF-8缂栫爜璇诲彇

        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")

            with open(file_path, 'r', encoding='utf-8') as file:

                text = file.read()

            return text

        except UnicodeDecodeError:

            # 濡傛灉UTF-8澶辫触锛屽皾璇旼BK缂栫爜锛堜腑鏂嘩indows甯哥敤锛?

            with open(file_path, 'r', encoding='gbk') as file:

                text = file.read()

            return text

    except Exception as e:

        print(f"浠嶵XT鏂囦欢涓彁鍙栨枃鏈嚭閿?{e}")

        raise Exception(f"浠嶵XT鏂囦欢涓彁鍙栨枃鏈嚭閿?{e}")



@app.route('/test_upload', methods=['POST'])

def test_upload():

    """娴嬭瘯鏂囦欢涓婁紶鍔熻兘"""

    result = {

        'status': 'received',

        'form_data': {},

        'file_info': None,

        'file_content': None

    }

    

    # 璁板綍琛ㄥ崟鏁版嵁

    for key in request.form:

        result['form_data'][key] = request.form[key]

    

    # 澶勭悊鏂囦欢

    if 'file' not in request.files:

        result['error'] = "No file part in the request"

        return jsonify(normalize_scores(result)), 400

        

    file = request.files['file']

    

    if file.filename == '':

        result['error'] = "No file selected"

        return jsonify(normalize_scores(result)), 400

        

    if file:

        original_filename = file.filename

        safe_filename = secure_filename(original_filename)

        file_ext = os.path.splitext(original_filename)[1].lower()

        

        result['file_info'] = {

            'original_filename': original_filename,

            'safe_filename': safe_filename,

            'extension': file_ext,

            'content_type': file.content_type

        }

        

        # 淇濆瓨涓存椂鏂囦欢

        temp_file = tempfile.NamedTemporaryFile(delete=False)

        file.save(temp_file.name)

        temp_path = temp_file.name

        temp_file.close()

        

        # 灏濊瘯璇诲彇鏂囦欢鍐呭

        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")

            if file_ext == '.txt':

                try:
                    pass  # 自动修复的空块
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")
                except Exception as e:
                    logger.error(f"发生错误: {str(e)}")

                    with open(temp_path, 'r', encoding='utf-8') as f:

                        content = f.read()

                except UnicodeDecodeError:

                    with open(temp_path, 'r', encoding='gbk') as f:

                        content = f.read()

                result['file_content'] = content[:500] + ('...' if len(content) > 500 else '')

            elif file_ext == '.docx':

                content = docx2txt.process(temp_path)

                result['file_content'] = content[:500] + ('...' if len(content) > 500 else '')

            else:

                result['file_content'] = "File content not displayed for this type"

        except Exception as e:

            result['error'] = f"Error reading file: {str(e)}"

        finally:

            # 鍒犻櫎涓存椂鏂囦欢

            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")

                os.unlink(temp_path)

            except:

                pass

    

    return jsonify(normalize_scores(result))



@app.route('/test_ocr', methods=['GET'])

def test_ocr():

    """娴嬭瘯OCR鍔熻兘"""

    # 娣诲姞涓€涓矾鐢辩敤浜庢祴璇昈CR鍔熻兘

    result = {"status": "testing"}

    

    # 鏌ョ湅鐜鍙橀噺

    result["env"] = {

        "DASHSCOPE_API_KEY": DASHSCOPE_API_KEY[:5] + "..." if DASHSCOPE_API_KEY else None,

        "DASHSCOPE_MODEL": DASHSCOPE_MODEL,

        "OCR_PROVIDER": OCR_PROVIDER

    }

    

    # 鏌ユ壘娴嬭瘯鍥剧墖

    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        # 鏌ユ壘涓婁紶鐨勫浘鐗囨枃浠?

        images = []

        for root, _, files in os.walk("static"):

            for file in files:

                if file.lower().endswith(('.jpg', '.jpeg')):

                    images.append(os.path.join(root, file))

                    

        if not images:

            result["error"] = "鏈壘鍒板浘鐗囨枃浠讹紝璇峰厛涓婁紶鍥剧墖鍒皊tatic鐩綍"

            return jsonify(normalize_scores(result))

            

        # 浣跨敤鎵惧埌鐨勭涓€寮犲浘鐗囪繘琛屾祴璇?

        test_image = images[0]

        result["test_image"] = test_image

        

        # 浣跨敤OCR澶勭悊鍥惧儚

        print(f"姝ｅ湪浣跨敤OCR鏈嶅姟澶勭悊鍥惧儚: {test_image}, 妯″紡: {OCR_PROVIDER}")

        ocr_result = ocr_service.process_image(test_image, method=OCR_PROVIDER)

        

        if ocr_result["success"]:

            result["success"] = True

            result["text"] = ocr_result["text"]

            result["method"] = ocr_result["method"]

        else:

            result["success"] = False

            result["error"] = ocr_result.get("error", "OCR璇嗗埆澶辫触")

            

    except Exception as e:

        result["success"] = False

        result["error"] = str(e)

        

    return jsonify(normalize_scores(result))



@app.route('/restart', methods=['GET'])

def restart_server():

    """閲嶅惎鏈嶅姟"""

    # 璁板綍閲嶅惎璇锋眰

    print("鏀跺埌閲嶅惎璇锋眰")

    

    # 杩斿洖閲嶅惎纭

    return jsonify(normalize_scores({))
        "success": True,

        "message": "鏈嶅姟鍣ㄥ皢鍦?绉掑悗閲嶅惎"

    })

    

    # 寮傛鎵ц閲嶅惎

    def restart_after_delay():

        time.sleep(5)

        os._exit(0)  # 寮哄埗閫€鍑鸿繘绋嬶紝璁╁閮ㄨ繘绋嬬鐞嗗櫒閲嶅惎鏈嶅姟

        

    # 鍒涘缓绾跨▼鎵ц閲嶅惎

    import threading

    restart_thread = threading.Thread(target=restart_after_delay)

    restart_thread.daemon = True

    restart_thread.start()



def check_format_compatibility(value):

    """娴嬭瘯鍊兼槸鍚﹀彲浠ュ畨鍏ㄧ敤浜庡瓧绗︿覆鏍煎紡鍖?""
"
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")

        # 灏濊瘯鍚勭鏍煎紡鍖栨搷浣滐紝鐪嬫槸鍚︿細鍑洪敊

        result1 = f"Test {value}"

        result2 = "Test %s" % value

        result3 = "Test {}".format(value)

        return True, "鏍煎紡鍖栧吋瀹?
"
    except Exception as e:

        return False, f"鏍煎紡鍖栦笉鍏煎: {str(e)}"



if __name__ == '__main__':

    # 鍒涘缓templates鍜宻tatic鐩綍锛堝鏋滀笉瀛樺湪锛?

    os.makedirs('templates', exist_ok=True)

    os.makedirs('static', exist_ok=True)



    # 璁剧疆鏃ュ織

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'server_debug.log')



    # 閰嶇疆鏃ュ織

    logging.basicConfig(
)
        level=logging.DEBUG,

        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

        handlers=[

            logging.FileHandler(log_file, 'a', 'utf-8'),

            logging.StreamHandler()

        ]

    )



    logger = logging.getLogger('server_external')

    logger.info("鏈嶅姟鍣ㄦ棩蹇楀垵濮嬪寲瀹屾垚")



    # 鍚姩Flask搴旂敤锛屼娇鐢?.0.0.0璁╁閮ㄧ綉缁滃彲璁块棶

    print("浣滄枃鑷姩鎵规敼绯荤粺鏈嶅姟鍚姩...")

    print("璁块棶鍦板潃锛歨ttp://127.0.0.1:5000 鎴?http://[鎮ㄧ殑IP鍦板潃]:5000")

    app.run(debug=True, host='0.0.0.0', port=5000) 









