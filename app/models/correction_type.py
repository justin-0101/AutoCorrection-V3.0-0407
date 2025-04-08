import enum

class CorrectionType(str, enum.Enum):
    """批改类型枚举"""
    AI = 'ai'           # AI批改
    HUMAN = 'human'     # 人工批改

    @classmethod
    def get_display_text(cls, type_value):
        """获取类型的显示文本"""
        type_text = {
            cls.AI.value: 'AI批改',
            cls.HUMAN.value: '人工批改'
        }
        return type_text.get(type_value, '未知类型') 