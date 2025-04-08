import asyncio
import math
import json

from test_article import *
from llm_func import *
from utils import *

SUBJECT = subject_3
ARTICLE = article_3

# 模拟API响应，用于离线测试
MOCK_MODE = False

MOCK_RESPONSES = {
    "spell_error": {
        "错别字扣分": "0",
        "解析": "未发现任何错别字，本项不扣分。"
    },
    "content_analysis": {
        "内容主旨得分": "18",
        "解析": {
            "主旨解析": "文章紧扣'好的故事是有力量的'这一主题，强调了好的中国故事在讲述者与受众之间建立情感联系、产生思想共鸣的功能，以及讲好中国故事对展现中国形象的重要性。文章的主旨与题目要求高度契合。",
            "论点解析": "文章论点清晰，主要包括：1.好的中国故事能够在讲述者与受众之间建立情感联系；2.好的中国故事应贯穿中国发展之'道'；3.讲好中国故事能够展现民族形象；4.青年应争做优秀的讲述人。这些论点层层递进，紧扣主题。",
            "论据解析": "文章引用了'文所以载道也'的古语和'能看到多远的未来，就能抵达多远的未来'的名言作为论据支撑。虽然具体事例不多，但通过对中国故事功能和意义的深入分析，使论证较为充实。",
            "思想情感解析": "文章表达了对中华文化的自信与热爱，以及对讲好中国故事、传播中国声音的热忱与责任感。思想积极健康，情感真挚，体现了作者作为新时代青年的担当意识。"
        }
    },
    "express_analysis": {
        "表达文采得分": "17",
        "解析": {
            "论证手法解析": "文章运用了多种论证方法。首先使用了比喻论证，将'好的故事'比作'细腻丝绸'，生动形象地突出了故事的柔软特质和力量。其次运用了道理论证，通过阐述中国故事的功能、特点和意义，论证了讲好中国故事的重要性。",
            "引经据典解析": "文章适当引用了典故和名言，如'文所以载道也'引用周敦颐的观点，表明了文章应当承载道理的思想；'如月之恒，如日之升'借用诗经中的句子，形象地描述了中国的发展态势；'能看到多远的未来，就能抵达多远的未来'这一哲理性名言，增强了文章的说服力。",
            "修辞手法解析": "文章运用了比喻、排比等修辞手法。'好的故事如同细腻丝绸'使用比喻，生动形象；'讲好中国故事，传播好中国声音，方能展现可爱可敬之中国形象'使用排比，增强了语言的节奏感和表达效果；'理论是灰色的，而中国故事色彩斑澜'使用对比，突出了中国故事的魅力。"
        }
    }
}


async def mock_handler_spell_error(article: str):
    return MOCK_RESPONSES["spell_error"]


async def mock_handler_content_analysis(subject: str, article: str):
    return MOCK_RESPONSES["content_analysis"]


async def mock_handler_express_analysis(subject: str, article: str):
    return MOCK_RESPONSES["express_analysis"]


async def mock_handler_summary(detail: dict):
    return """总评：
本篇作文立意明确，紧扣"好的故事是有力量的"这一主题，从中国故事的角度展开论述，思路清晰，内容充实。在内容方面，文章主旨鲜明，论点清晰，思想健康，情感真挚，获得高分。在表达方面，文章使用了比喻、排比等修辞手法，引用了古语和名言，增强了文章的说服力和表现力，语言表达丰富多彩。作文未发现错别字，规范得体。
建议：
1. 可以增加一些具体事例，使论据更加丰富；
2. 可以进一步丰富修辞手法的运用，使表达更加生动。
总体而言，这是一篇很好的议论文，主题突出，论证有力，表达得体。"""


async def main():
    n_words = count_chinese_characters(ARTICLE)
    upper_limit, deduct_by_words = words_count_handler(n_words)

    if MOCK_MODE:
        results = await asyncio.gather(
            mock_handler_spell_error(ARTICLE),
            mock_handler_content_analysis(SUBJECT, ARTICLE),
            mock_handler_express_analysis(SUBJECT, ARTICLE)
        )
    else:
        results = await asyncio.gather(
            handler_spell_error(ARTICLE),
            handler_content_analysis(SUBJECT, ARTICLE),
            handler_express_analysis(SUBJECT, ARTICLE)
        )
    
    results_spell = results[0]
    results_content = results[1]
    results_express = results[2]

    factor = upper_limit / 60
    mark = math.ceil(factor * (int(results_express["表达文采得分"]) + int(results_content["内容主旨得分"]) + int(
        (20 - int(results_spell["错别字扣分"])))))
    detail = {"错别字解析": results_spell["解析"], "内容主旨解析": results_content["解析"], "表达文采解析": results_express["解析"]}
    
    if MOCK_MODE:
        summary = await mock_handler_summary(detail)
    else:
        summary = await handler_summary(detail)

    print(f"===== 作文自动批改结果 =====")
    print(f"字数统计: {n_words}字")
    print(f"错别字扣分: {results_spell['错别字扣分']}")
    print(f"内容主旨得分: {results_content['内容主旨得分']}")
    print(f"表达文采得分: {results_express['表达文采得分']}")
    print(f"总分: {mark}/100")
    print(f"===== 评语 =====")
    print(f"{summary}")


if __name__ == '__main__':
    asyncio.run(main())
