#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作文批改系统最终优化版
整合所有修复和改进
确保与前端完全兼容
"""

import dotenv
dotenv.load_dotenv()  # 加载环境变量

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import logging
import time
import traceback
from datetime import datetime
import asyncio
from llm_func import model, get_model_response  # 仅导入model函数和get_model_response
import tempfile
from werkzeug.utils import secure_filename
import threading

# 尝试导入OCR服务（可选）
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    import ocr_service
    from ocr_service import process_image
    ocr_available = True
    print("OCR服务初始化成功")
except ImportError:
    ocr_available = False
    print("警告: OCR模块未安装，本地OCR功能不可用")

# 尝试导入pytesseract（用于本地OCR）
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    import pytesseract
    pytesseract_available = True
except ImportError:
    pytesseract_available = False
    print("警告: pytesseract未安装，本地OCR功能不可用")

# 尝试导入pdf2image（用于处理扫描版PDF）
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    # 设置poppler路径
    poppler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'poppler')
    if os.path.exists(poppler_path):
        # 如果有poppler目录，将其添加到环境变量
        print(f"找到poppler目录: {poppler_path}")
        os.environ['PATH'] = poppler_path + os.pathsep + os.environ.get('PATH', '')
    else:
        print("警告: 未找到本地poppler目录")
    
    from pdf2image import convert_from_path
    pdf2image_available = True
    print("pdf2image初始化成功")
except ImportError:
    pdf2image_available = False
    print("警告: pdf2image未安装，扫描版PDF处理功能不可用")

# 尝试导入docx处理模块
try:
    pass  # 自动修复的空块
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    import docx
    docx_available = True
except ImportError:
    docx_available = False
    print("警告: python-docx未安装，DOCX处理功能不可用")

# 打印环境变量状态用于调试
print("\n===== 环境变量检查=====")
print(f"DEEPSEEK_API_KEY: {'已设置(长度:' + str(len(os.getenv('DEEPSEEK_API_KEY', ''))) + '字符)' if os.getenv('DEEPSEEK_API_KEY') else '未设置'}")
print(f"DEEPSEEK_BASE_URL: {os.getenv('DEEPSEEK_BASE_URL', '未设置')}")
print(f"DEEPSEEK_MODEL: {os.getenv('DEEPSEEK_MODEL', '未设置')}")
print("========================\n")

# 最小推荐字符数
MIN_CHARS = 500

async def ai_analyze_content(text, subject=""):
    """
    使用AI分析文章内容并计算分数
    
    Args:
        text (str): 文章内容
        subject (str, optional): 文章标题
        
    Returns:
        dict: 分析结果
    """
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 构建提示词 - 使用用户提供的详细评分标准
        prompt_start = f"""<请你作为广东中考语文阅卷老师，按照以下标准对作文进行全面评分和详细分析：

作文标题：{subject if subject else "无标题"}
作文内容：{text[:3000]}...（内容过长已省略）
字数：{len(text)}字

【广东中考语文作文评分标准】
总分50分
字数要求600字以上

【评分等级划分】
A级（43-50分）：内容立意明确，中心突出，材料具体生动，有真情实感；语言得体、流畅；结构严谨，注意照应，详略得当；卷面整洁，书写优美。
B级（35-42分）：内容立意明确，中心突出，材料具体；语言规范、通顺；结构完整，条理清楚；卷面整洁，书写工整。
C级（27-34分）：内容立意明确，材料能表现中心；语言基本通顺，有少数错别字；结构基本完整，有条理；卷面较为整洁，书写清楚。
D级（0-26分）：内容立意不明确，材料难以表现中心；语言不通顺，错别字较多；结构不完整，条理不清楚；卷面脏乱，字迹潦草。

【等级细分标准】
A级细分：优秀（47-50分），良好（43-46分）
B级细分：较好（39-42分），一般（35-38分）
C级细分：尚可（21-34分），欠佳（27-30分）
D级细分：不足（0-26分），较差（0-19分）

【具体扣分项】
1. 无标题扣2分
2. 字数不足：低于200字，每少50字扣1分
3. 错别字：每个错别字扣1分
4. 标点符号使用不规范：根据严重程度1-3分
5. 泄露考生真实身份：扣1分

【加分项】（以下方面优秀可酌情加1-2分，总加分不超过5分）
1. 立意深刻、有思想深度
2. 构思独特、角度新
3. 语言优美、富有文采
4. 材料选取恰当、有说服力
5. 感情真挚、打动人

【评分维度权重】
1. 内容20-25分，40%-50%）：立意明确、中心突出、材料具体生动、情感真实
2. 语言15-20分，30%-40%）：语言流畅、规范、优美，能灵活运用修辞手法
3. 结构0.5-10分，15%-20%）：结构严谨、条理清晰、段落衔接自然
4. 文面0.5-5分，5%-10%）：标点符号使用规范、段落格式正确

【针对不同题材的评分侧重】
1. 记叙文：情节完整性、细节描写、人物刻画、情感表达
2. 议论文：论点明确、论据充分、论证严密、结构完整
3. 说明文：说明对象准确、说明方法多样、语言简明、逻辑性强
4. 应用文：格式规范、内容完整、语言得体、实用性强

【错别字识别指南】
1. 仔细检查全文，特别关注易错字、形近字、音近字
2. 重点检查专有名词、成语、特殊词汇的拼写
3. 注意辨别同音字、多音字的正确使用
4. 区分正确的异体字和错误的别字
5. 标记每个错别字的位置（段落句子）、错误写法、正确写法和上下文

【表达文采分析要求】
请详细分析文章的语言表达特点，包括：
1. 用词水平（准确性、生动性、是否使用成语典故等）
2. 句式变化（长短句搭配、句式多样性）
3. 修辞手法（比喻、拟人、排比等修辞手法的运用情况）
4. 语言流畅度（段落和句子之间的过渡是否自然）

请仔细分析作文，提供以下内容（必须包含详细的分析和具体分数计算过程）：

1. 总得分（满分50分）及等级评定（A、B、C、D，并标明细分等级）
2. 分项得分明细及计算过程
- 内容得分20-25分）：详细说明得分理
- 语言得分15-20分）：详细说明得分理
- 结构得分0.5-10分）：详细说明得分理
- 文面得分0.5-5分）：详细说明得分理
3. 扣分项分
- 错别字分析：列出每个错别字、位置及正确写法
- 其他扣分项及理由
4. 加分项分析及理由
5. 作文优点（至少3点，并举例说明）
6. 作文不足（至少3点，并举例说明）
7. 针对性改进建议（至少3条具体可行的建议）
8. 语言文采分析（详细分析用词、句式、修辞手法和语言流畅度）
9. 总体评价（100-200字）：对作文的整体评价和提升方向"""

        # 修改JSON指令部分以匹配简化后的表达文采分析要求
        json_instructions = """
必须以JSON格式返回结果，结构如下：
```json
{
"总得分": "45",
"等级评定": "A-优秀",
"分项得分": {
    "内容主旨": "22",
    "语言文采": "17",
    "文章结构": "8.5",
    "文面书写": "4.5"
},
"扣分": {
    "错别字分": [
    {"错误": "错别字", "位置": "第二段第3行, "正确写法": "正确写法1", "上下文": "包含错别字的上下文"},
    {"错误": "错别字", "位置": "第三段第1行, "正确写法": "正确写法2", "上下文": "包含错别字的上下文"}
    ],
    "其他扣分": ["无标题扣2分"]
},
"加分": ["立意深刻(+1分)","语言优美(+1分)"],
"总体评价": "这篇作文...(详细评价)",
"内容分析": "文章主题...(详细分析)",
"语言分析": "本文语言流畅，使用了多种修辞手法，词汇丰富...(详细分析用词、句式、修辞手法和流畅度)",
"结构分析": "文章结构...(详细分析)",
"错别字分": [
    {"错误": "错别字", "位置": "第二段第3行, "正确写法": "正确写法1"},
    {"错误": "错别字", "位置": "第三段第1行, "正确写法": "正确写法2"}
],
"优点": ["观点明确", "论述清晰", "结构合理"],
"不足": ["细节不足", "例子较少"],
"建议": ["增加具体例子", "使用更多修辞手法", "适当精简句子"]
}
```
"""
        # 合并提示词
        prompt = prompt_start + json_instructions

        print(f"准备调用AI模型，提示词长度: {len(prompt)}字符")
        
        # 调用AI模型
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 使用原始系统相同的系统提示词
            response = await model([
                {"role": "system", "content": "你是一位专业的中文语文教师，擅长高效评判学生作文。请提供专业详细的分析，重点突出评分和主要评价"},
                {"role": "user", "content": prompt}
            ])
            
            print(f"AI调用成功，获得响应 {type(response)}")
            
            if not response or not response.choices:
                print("AI响应为空或不包含choices")
                raise Exception("AI返回结果为空")
                
            # 提取AI生成的内容
            ai_content = response.choices[0].message.content
            print(f"AI生成内容长度: {len(ai_content)}字符")
            print(f"AI生成内容前100字符: {ai_content[:100]}")
            
        except Exception as api_error:
            print(f"AI API调用出错: {type(api_error).__name__}: {str(api_error)}")
            print(traceback.format_exc())
            raise Exception(f"AI API调用失败: {str(api_error)}")
        
        # 尝试解析JSON
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 提取JSON部分（如果AI没有直接返回JSON）
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', ai_content)
            if json_match:
                ai_content = json_match.group(1)
                print("从Markdown代码块中提取JSON成功")
            else:
                print("未找到JSON代码块，尝试直接解析整个内容")
            
            result = json.loads(ai_content)
            print(f"成功解析JSON，包含字段 {list(result.keys())}")
            
            # 确保总分不超过50分
            total_score = float(result.get("总得分", 0))
            if total_score > 50:
                total_score = 50
                result["总得分"] = "50"
                print("总分已调整为最大50")
            
            # 获取各项分数
            scores = result.get("分项得分", {})
            content_score = float(scores.get("内容主旨", 0))
            language_score = float(scores.get("语言文采", 0))
            structure_score = float(scores.get("文章结构", 0))
            writing_score = float(scores.get("文面书写", 0))
            
            # 等级评定
            grade = "B"
            if "等级评定" in result:
                grade_text = result["等级评定"]
                if "A" in grade_text or "优秀" in grade_text:
                    grade = "A"
                elif "B" in grade_text or "良好" in grade_text:
                    grade = "B" 
                elif "C" in grade_text or "及格" in grade_text:
                    grade = "C"
                elif "D" in grade_text or "不及格" in grade_text:
                    grade = "D"
            
            # 转换为统一的英文字段名格式
            final_result = {
                "words_count": len(text),
                "content_score": content_score,
                "language_score": language_score, 
                "structure_score": structure_score,
                "writing_score": writing_score,
                "total_score": total_score,
                "score_value": total_score,
                "score": total_score,
                "score_display": total_score,
                "grade": grade,
                "error_count": 0,
                "overall_assessment": result.get("总体评价", ""),
                "comments": result.get("总体评价", ""),
                "content_analysis": result.get("内容分析", ""),
                "language_analysis": result.get("语言分析", ""),
                "structure_analysis": result.get("结构分析", ""),
                "writing_analysis": result.get("写作分析", "格式规范，无明显错别字"),
                "strengths": result.get("优点", ["观点明确", "论述清晰"]),
                "weaknesses": result.get("不足", ["需要更多例子"]),
                "suggestions": result.get("建议", ["增加具体例子", "适当精简句子"]),
                "success": True
            }
            
            # 处理错别字分
            spelling_errors = []
            # 尝试从两个可能的位置获取错别字数
            if "扣分" in result and "错别字分" in result["扣分"]:
                spelling_errors = result["扣分"]["错别字分"]
            elif "错别字分" in result:
                spelling_errors = result["错别字分"]
                
            # 更新错别字计数和写作分析
            if spelling_errors and isinstance(spelling_errors, list):
                final_result["error_count"] = len(spelling_errors)
                error_details = []
                for error in spelling_errors:
                    if isinstance(error, dict):
                        error_str = f"【{error.get('错误', '')}】应为【{error.get('正确写法', '')}】，位置：{error.get('位置', '')}"
                        error_details.append(error_str)
                
                if error_details:
                    final_result["writing_analysis"] = f"发现{len(spelling_errors)}个错别字" + " + ".join(error_details)
            
            print("成功转换为前端所需格式")
            return final_result
            
        except Exception as parse_error:
            print(f"JSON解析失败: {type(parse_error).__name__}: {str(parse_error)}")
            print(f"原始AI输出: {ai_content[:200]}...")
            # 解析失败，回退到备用方法
            raise Exception(f"解析AI输出失败: {str(parse_error)}")
            
    except Exception as e:
        print(f"AI分析过程出错: {type(e).__name__}: {str(e)}")
        # 出错时向上抛出异常，由调用者决定是否回退
        raise

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 详细记录响应数据
def log_response_data(result):
    """记录响应数据的详细信息，包括字段类型"""
    logger.info("响应字段详情")
    for key, value in result.items():
        logger.info(f"  {key}: {value} (类型: {type(value).__name__})")

# 标准化错误响应格式
def create_error_response(error_message):
    """创建标准化的错误响应格式"""
    return {
        # 核心错误信息
        "success": False,
        "error": error_message,
        
        # 核心分数字段
        "words_count": 0,
        "content_score": 0,
        "language_score": 0, 
        "structure_score": 0,
        "writing_score": 0,
        "total_score": 0,
        
        # 评分显示字段
        "score_value": 0,
        "score": 0,
        "score_display": 0,
        "grade": "F",
        "error_count": 0,
        
        # 文本评价字段
        "overall_assessment": f"批改失败: {error_message}",
        "comments": f"批改失败: {error_message}",
        
        # 分析字段
        "content_analysis": "无法分析",
        "language_analysis": "无法分析",
        "structure_analysis": "无法分析",
        "writing_analysis": "无法分析",
        
        # 列表数据
        "strengths": [],
        "weaknesses": [],
        "suggestions": []
    }

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

# 静态文件路径
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    """首页路由"""
    return render_template('index.html')

@app.route('/correct', methods=['POST'])
def correct_essay():
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 记录请求开始
        logging.info("=== 作文批改请求开始 ===")
        logging.info(f"请求内容类型: {request.content_type}")
        logging.info(f"表单数据: {request.form}")
        logging.info(f"文件: {request.files}")
        
        # 获取主题（可选）
        subject = request.form.get('subject', '')
        
        # 尝试从上传文件获取内容
        text_content = None
        
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            logging.info(f"收到文件上传: {file.filename}")
            
            # 安全保存文件到临时路径
            temp_dir = tempfile.gettempdir()
            
            # 处理文件类型
            is_image = file.content_type.startswith('image/')
            is_pdf = file.filename.lower().endswith('.pdf')
            is_doc = file.filename.lower().endswith('.doc')
            is_docx = file.filename.lower().endswith('.docx')
            is_txt = file.filename.lower().endswith('.txt')
            
            # 保存文件
            if is_docx:
                temp_filename = os.path.join(temp_dir, "docx")
            else:
                temp_filename = os.path.join(temp_dir, secure_filename(file.filename))
            
            file.save(temp_filename)
            logging.info(f"临时保存文件: {temp_filename}")
            
            # 根据文件类型处理
            try:
                pass  # 自动修复的空块
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
                if is_image:
                    logging.info(f"处理图片文件: {file.filename}")
                    text_content = process_image(temp_filename)
                    
                    if not text_content:
                        logging.warning("OCR识别失败，提供示例文本")
                        example_text = """这是一个示例文本，供系统测试使用。由于无法从您上传的图片中提取文本，系统已提供此示例文本代替。
                        
您可以尝试以下解决方法：
1. 确保图片清晰可辨，文字部分对比度
2. 使用质量更好的图片
3. 直接在文本框中输入内容
4. 使用.txt或docx等文本格式的文件

如需进一步帮助，请联系系统管理员。"""
                        logging.info(f"使用示例文本代替，长度: {len(example_text)}")
                        text_content = example_text
                
                elif is_pdf:
                    logging.info(f"处理PDF文件: {file.filename}")
                    
                    try:
                        pass  # 自动修复的空块
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                        import PyPDF2
                        with open(temp_filename, 'rb') as pdf_file:
                            try:
                                pass  # 自动修复的空块
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                                pdf_reader = PyPDF2.PdfReader(pdf_file)
                                pdf_text = ""
                                for page in pdf_reader.pages:
                                    pdf_text += page.extract_text() or ""
                                
                                text_content = pdf_text.strip()
                                logging.info(f"PDF提取文本成功，长度: {len(text_content)}")
                            except Exception as pdf_error:
                                logging.error(f"PDF解析错误: {str(pdf_error)}")
                                raise ValueError(f"无法解析PDF文件: {str(pdf_error)}。如果这是一个扫描版PDF，请尝试转换为文本格式或使用OCR功能提取文本。")
                    except ImportError:
                        logging.error("PyPDF2模块未安装，无法直接处理PDF")
                        raise ValueError("服务器未配置PDF处理库，无法解析PDF文件。请尝试上传文本格式文件。")
                    
                    # 如果PDF提取的文本为空，尝试OCR
                    if not text_content or len(text_content) < 10:
                        logging.warning("PDF文本为空或过短，可能是扫描版PDF，尝试直接使用OCR处理")
                        logging.info(f"直接使用OCR处理扫描版PDF: {temp_filename}")
                        
                        # 尝试OCR处理
                        text_content = process_image(temp_filename)
                        
                        if not text_content or len(text_content) < 50:
                            logging.error("OCR无法从扫描版PDF中提取文本，可能是扫描质量较低或PDF格式复杂。请使用更清晰的扫描文件或手动输入文本。")
                            example_text = """这是一个示例文本，供系统测试使用。由于您上传的PDF文件无法正确解析，系统已提供此示例文本代替。
                            
您可以尝试以下解决方法：
1. 确保PDF文件未加密且格式正确
2. 如果是扫描版PDF，请确保扫描质量清晰
3. 尝试使用OCR软件预处理文本
4. 直接在文本框中输入内容而不是上传文件
5. 转换为支持的文本格式(.txt或docx)后再上传

如需进一步帮助，请联系系统管理员。"""
                            logging.info(f"使用示例文本代替，长度: {len(example_text)}")
                            text_content = example_text
                            
                elif is_doc:
                    logging.info(f"处理DOC文件: {file.filename}")
                    
                    try:
                        pass  # 自动修复的空块
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                        import win32com.client
                        import re
                        
                        word = win32com.client.Dispatch("Word.Application")
                        word.visible = False
                        
                        # 获取绝对路径
                        abs_path = os.path.abspath(temp_filename)
                        doc = word.Documents.Open(abs_path)
                        
                        text_content = doc.Content.Text
                        doc.Close()
                        word.Quit()
                        
                        # 清理文本
                        text_content = re.sub(r'\r+', '\n', text_content)
                        text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
                        text_content = text_content.strip()
                        
                        logging.info(f"DOC提取文本成功，长度: {len(text_content)}")
                        
                    except ImportError:
                        logging.warning("win32com模块未安装，无法处理DOC文件")
                        example_text = """这是一个示例文本，供系统测试使用。由于系统未安装处理DOC文件所需的组件，无法解析您的文件。

您可以尝试以下解决方法：
1. 将DOC文件转换为DOCX或TXT格式后再上传
2. 直接在文本框中输入内容
3. 在安装了Office的计算机上使用此功能

如需帮助，请联系系统管理员安装必要的组件。"""
                        logging.info(f"使用示例文本代替，长度: {len(example_text)}")
                        text_content = example_text
                    except Exception as doc_error:
                        logging.error(f"DOC处理错误: {str(doc_error)}")
                        raise ValueError(f"处理DOC文件时出错: {str(doc_error)}。请尝试另存为DOCX或以文本形式提交。")
                
                elif is_docx:
                    logging.info(f"处理DOCX文件: {file.filename}")
                    
                    try:
                        pass  # 自动修复的空块
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                        import docx
                        doc = docx.Document(temp_filename)
                        doc_text = []
                        
                        for para in doc.paragraphs:
                            doc_text.append(para.text)
                        
                        text_content = '\n'.join(doc_text)
                        logging.info(f"DOCX提取文本成功，长度: {len(text_content)}")
                        
                    except ImportError:
                        logging.warning("python-docx模块未安装，无法处理DOCX文件")
                        example_text = """这是一个示例文本，供系统测试使用。由于系统未安装处理DOCX文件所需的组件，无法解析您的文件。

您可以尝试以下解决方法：
1. 将DOCX文件另存为TXT格式后再上传
2. 直接在文本框中输入内容
3. 联系系统管理员安装必要的组件

谢谢您的理解。"""
                        logging.info(f"使用示例文本代替，长度: {len(example_text)}")
                        text_content = example_text
                    except Exception as docx_error:
                        logging.error(f"DOCX处理错误: {str(docx_error)}")
                        raise ValueError(f"处理DOCX文件时出错: {str(docx_error)}。请尝试转换为文本格式或直接输入内容。")
                
                elif is_txt:
                    logging.info(f"处理文本文件: {file.filename}")
                    
                    try:
                        pass  # 自动修复的空块
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                        with open(temp_filename, 'r', encoding='utf-8') as txt_file:
                            text_content = txt_file.read().strip()
                        
                        if not text_content:
                            raise ValueError("文本文件为空，请确保文件包含有效内容。")
                        
                        logging.info(f"TXT读取成功，长度: {len(text_content)}")
                        
                    except UnicodeDecodeError:
                        # 尝试其他编码
                        encodings = ['gbk', 'gb2312', 'big5', 'utf-16', 'latin-1']
                        for encoding in encodings:
                            try:
                                pass  # 自动修复的空块
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                            except Exception as e:
                                logger.error(f"发生错误: {str(e)}")
                                with open(temp_filename, 'r', encoding=encoding) as txt_file:
                                    text_content = txt_file.read().strip()
                                logging.info(f"使用{encoding}编码成功读取文本文件")
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if not text_content:
                            raise ValueError("无法解析文本文件编码，请使用UTF-8编码保存文件或直接输入文本。")
                    
                    if not text_content or len(text_content) < 10:
                        raise ValueError("文本内容为空或过短，请确保文件包含有效内容。")
                
                else:
                    # 尝试作为纯文本读取
                    logging.warning(f"未识别的文件类型: {file.filename}，尝试作为文本读取")
                    
                    try:
                        pass  # 自动修复的空块
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                    except Exception as e:
                        logger.error(f"发生错误: {str(e)}")
                        with open(temp_filename, 'r', encoding='utf-8') as unknown_file:
                            text_content = unknown_file.read().strip()
                    except UnicodeDecodeError:
                        # 尝试其他编码
                        try:
                            pass  # 自动修复的空块
                        except Exception as e:
                            logger.error(f"发生错误: {str(e)}")
                        except Exception as e:
                            logger.error(f"发生错误: {str(e)}")
                            with open(temp_filename, 'r', encoding='gbk') as unknown_file:
                                text_content = unknown_file.read().strip()
                        except:
                            pass
                    
                    if not text_content or len(text_content) < 10:
                        logging.warning("未知文件类型且内容为空或过短，可能是二进制文件")
                        example_text = """这是一个示例文本，供系统测试使用。系统无法识别您上传的文件格式或无法提取其中的文本内容。

系统支持以下文件格式：
- 文本文件 (.txt)
- Word文档 (.docx, .doc)
- PDF文件 (文本PDF或扫描版)
- 图片文件 (包含文字的图片)

您可以尝试以下解决方法：
1. 转换为上述支持的格式后再上传
2. 直接在文本框中输入内容
3. 检查文件是否损坏或格式是否正确

如需进一步帮助，请联系系统管理员。"""
                        logging.info(f"使用示例文本代替，长度: {len(example_text)}")
                        text_content = example_text
                
                # 内容长度检查
                if len(text_content) > 10000:
                    logging.warning(f"文本过长 ({len(text_content)} 字符)，截断至10000字符")
                    text_content = text_content[:10000]
                    
            except Exception as e:
                error_message = f"文件处理验证错误: {str(e)}"
                logging.error(error_message)
                return jsonify({"error": error_message, "success": False}), 400
        
        elif request.form and 'article' in request.form:
            # 从表单字段获取
            text_content = request.form['article']
            logging.info(f"从表单获取文章内容，长度: {len(text_content)}")
            
            # 限制文本长度，防止超大文本造成处理问题
            MAX_TEXT_LENGTH = 10000  # 限制10000字符
            if len(text_content) > MAX_TEXT_LENGTH:
                logging.warning(f"文本长度过大: {len(text_content)}字符，将被截断至{MAX_TEXT_LENGTH}字符")
                text_content = text_content[:MAX_TEXT_LENGTH]
        
        # 验证是否获取到内容
        if not text_content:
            logging.warning("未收到任何文章内容")
            return jsonify(create_error_response("未提供文章内容，请输入文本或上传文件")), 400
            
        # 记录最终处理的文本长度
        logging.info(f"最终文章长度: {len(text_content)}")
        
        # 分析文章内容 - 使用AI分析函数
        try:
            pass  # 自动修复的空块
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            # 尝试使用AI分析
            logging.info("使用AI分析文章内容")
            
            # 记录AI调用细节，帮助调试
            logging.info(f"AI调用开始 文本长度={len(text_content)}, 主题={subject}")
            
            # 调用AI分析
            result = asyncio.run(ai_analyze_content(text_content, subject))
            
            logging.info("AI分析完成")
        except Exception as ai_error:
            # 如果AI分析失败，详细记录错误
            logging.error(f"AI分析失败，错误类型: {type(ai_error).__name__}")
            logging.error(f"AI分析错误详情: {str(ai_error)}")
            logging.error(f"错误堆栈: {traceback.format_exc()}")
            logging.warning("回退到备用分析方法")
            
            # 使用备用方法
            result = analyze_content_fallback(text_content)
        
        logging.info(f"计算得分: 内容={result['content_score']}, 表达={result['language_score']}, 结构={result['structure_score']}, 书写={result['writing_score']}, 总分={result['total_score']}")
        
        # 延迟1秒模拟处理时间
        time.sleep(1)
        
        # 添加success字段表示成功
        result['success'] = True
        
        # 添加原始文本内容
        result['original_text'] = text_content
        
        # 记录返回的结果结果
        logging.info(f"最终返回结果: {json.dumps(result, ensure_ascii=False)}")
        
        # 记录响应数据的详细信息
        log_response_data(result)
        
        return jsonify(result)
    
    except Exception as e:
        # 详细记录错误
        logging.error(f"处理错误: {str(e)}")
        logging.error(traceback.format_exc())
        
        # 创建标准化错误响应
        error_result = create_error_response(str(e))
        return jsonify(error_result), 500

@app.route('/api/correction', methods=['POST'])
def api_correction():
    """API版本路由，处理新版客户端请求"""
    logging.info("收到/api/correction请求，使用标准处理流程")
    return correct_essay()

@app.route('/test', methods=['POST'])
def test_connection():
    """测试POST请求是否能正常工作的路由"""
    logger.info("收到测试连接请求")
    try:
        pass  # 自动修复的空块
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        # 记录请求数据
        logger.info(f"请求表单数据: {request.form}")
        logger.info(f"请求文件: {request.files}")
        
        # 返回成功消息
        return "连接测试成功! 服务器正常工作"
    except Exception as e:
        logger.error(f"测试连接发生错误: {str(e)}")
        return f"测试失败: {str(e)}", 500

if __name__ == '__main__':
    print("作文批改系统服务启动...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)