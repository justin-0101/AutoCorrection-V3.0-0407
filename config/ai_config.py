"""
AI配置模块
提供AI服务所需的各项配置参数
"""

import os

# AI服务配置
AI_CONFIG = {
    # API配置
    'API_KEY': os.environ.get('DEEPSEEK_API_KEY', ''),
    'BASE_URL': os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
    'MODEL': os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat'),
    
    # 模型参数
    'TEMPERATURE': float(os.environ.get('AI_TEMPERATURE', '0.7')),
    'MAX_TOKENS': int(os.environ.get('AI_MAX_TOKENS', '4000')),
    'TOP_P': float(os.environ.get('AI_TOP_P', '0.95')),
    'TIMEOUT': int(os.environ.get('AI_TIMEOUT', '120')),
    
    # 批改系统提示词
    'CORRECTION_SYSTEM_PROMPT': os.environ.get('CORRECTION_SYSTEM_PROMPT', 
        '你是一位专业的中文作文评价老师。你的任务是批改学生的作文。'
        '你需要指出作文中的错误并给出修改建议。'
        '同时评价作文的内容、语言、结构和书写，并提供改进建议和评分。'
    ),
    
    # 分析系统提示词
    'ANALYSIS_SYSTEM_PROMPT': os.environ.get('ANALYSIS_SYSTEM_PROMPT',
        '你是一位专业的文本分析专家。请对提供的作文进行深度分析，'
        '包括主题、关键词、情感倾向、复杂度、写作风格等方面。'
        '分析要客观、全面、专业。'
    ),
    
    # 评分标准
    'SCORING_CRITERIA': {
        'content': {
            'weight': 0.3,
            'description': '内容评分标准：文章是否立意鲜明、是否切题、是否有深度'
        },
        'language': {
            'weight': 0.3,
            'description': '语言评分标准：语言使用、词汇丰富性、表达准确性'
        },
        'structure': {
            'weight': 0.2,
            'description': '结构评分标准：文章整体结构、段落连贯性、开头结尾'
        },
        'writing': {
            'weight': 0.2,
            'description': '书写评分标准：格式规范、标点正确、整洁美观'
        }
    },
    
    # 支持的AI功能
    'FEATURES': {
        'error_correction': True,  # 错误修正
        'scoring': True,           # 评分
        'feedback': True,          # 反馈
        'suggestions': True,       # 改进建议
        'spelling_check': True,    # 拼写检查
    },
    
    # 调试模式
    'DEBUG': os.environ.get('AI_DEBUG', 'False').lower() == 'true'
}

# AI评分等级
SCORING_RULES = {
    'excellent': {
        'range': (90, 100),
        'description': '优秀：内容、立意、表达、结构出色，令人印象深刻。'
    },
    'good': {
        'range': (80, 89),
        'description': '良好：内容切题、流畅、结构规范、有创意。'
    },
    'satisfactory': {
        'range': (70, 79),
        'description': '一般：内容基本切题、基本流畅、结构基本规范、平淡。'
    },
    'pass': {
        'range': (60, 69),
        'description': '及格：内容不够切题、不够流畅、结构不够规范、稍有混乱。'
    },
    'fail': {
        'range': (0, 59),
        'description': '不及格：内容不切题、不流畅、结构混乱、不规范。'
    }
}

# 错误类型
ERROR_TYPES = {
    'grammar': '语法',
    'spelling': '拼写',
    'punctuation': '标点',
    'word_choice': '用词不当',
    'verb_tense': '时态',
    'subject_verb_agreement': '主谓一致',
    'article': '冠词',
    'preposition': '介词',
    'pronoun': '代词',
    'word_order': '词序',
    'redundancy': '冗余',
    'missing_word': '缺词',
    'collocation': '搭配',
    'ambiguity': '歧义',
    'incomplete_sentence': '句子不完整',
    'run_on_sentence': '句子过长',
    'fragment': '句子片段',
    'misplaced_modifier': '修饰语错位',
    'dangling_modifier': '悬垂修饰语',
    'parallelism': '平行结构',
    'tone': '语气',
    'formality': '正式性',
    'conciseness': '简洁性',
    'clarity': '清晰度',
    'coherence': '连贯性',
    'unity': '统一性',
    'emphasis': '强调',
    'voice': '语态',
    'style': '风格',
    'other': '其他'
}

