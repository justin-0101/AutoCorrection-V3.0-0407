"""
测试Essay模型中source_type的处理
特别关注隐藏字符问题
"""

from app.models.essay import Essay, EssaySourceType
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('essay_test')

# 测试不同输入形式
test_values = [
    'paste',
    'paste ',  # 末尾有空格
    ' paste',  # 前面有空格
    '\tpaste',  # 前面有制表符
    'paste\r',  # 有回车符
    'paste\n',  # 有换行符
    EssaySourceType.paste.value,  # 枚举值
    EssaySourceType.paste,        # 枚举实例
]

logger.info('===== 开始测试可能的隐藏字符问题 =====')

for i, val in enumerate(test_values):
    logger.info(f'测试 #{i+1}: 原始值 repr={repr(val)}')
    essay = Essay(title='测试', content='内容', user_id=1, source_type=val)
    logger.info(f'结果: source_type={essay.source_type}, repr={repr(essay.source_type)}')
    
    # 检查最终值是否匹配预期
    expected = 'paste'
    if essay.source_type != expected:
        logger.warning(f'不匹配! 期望值={expected}, 实际值={essay.source_type}')
    else:
        logger.info('匹配成功')
    logger.info('-' * 50)

logger.info('===== 测试结束 =====')

# 通过修改validate_source_type方法来添加更多调试信息
import types
old_validate = Essay.validate_source_type

def enhanced_validate(self, key, value):
    """增强的验证方法，添加更多调试信息"""
    logger.info(f"调用validate_source_type: 原始输入值: {repr(value)}, 类型: {type(value)}")
    
    # 如果是字符串，进行额外检查
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned != value:
            logger.warning(f"字符串包含前导/尾随空白: '{value}' -> '{cleaned}'")
        
        # 检查字符编码
        for i, c in enumerate(value):
            if ord(c) > 127:  # 非ASCII字符
                logger.warning(f"位置 {i} 的非ASCII字符: {repr(c)}, Unicode: {ord(c)}")
    
    result = old_validate(self, key, value)
    logger.info(f"验证结果: {repr(result)}")
    return result

# 临时替换方法以获取更多调试信息
Essay.validate_source_type = enhanced_validate

logger.info('\n===== 使用增强验证测试 =====')
for enum_val in EssaySourceType:
    # 测试枚举值
    logger.info(f'测试枚举值: {enum_val.name} = {enum_val.value}')
    essay = Essay(title='测试', content='内容', user_id=1, source_type=enum_val.value)
    logger.info(f'结果: source_type={essay.source_type}')
    logger.info('-' * 50)

logger.info('===== 测试完成 =====') 