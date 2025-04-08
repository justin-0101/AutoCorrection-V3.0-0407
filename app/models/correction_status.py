import enum

class CorrectionStatus(str, enum.Enum):
    """批改状态枚举"""
    PENDING = 'pending'       # 等待批改
    PROCESSING = 'processing' # 批改中
    COMPLETED = 'completed'   # 已完成
    FAILED = 'failed'        # 失败

    @classmethod
    def get_display_text(cls, status):
        """获取状态的显示文本"""
        status_text = {
            cls.PENDING.value: '等待批改',
            cls.PROCESSING.value: '批改中',
            cls.COMPLETED.value: '已完成',
            cls.FAILED.value: '失败'
        }
        return status_text.get(status, '未知状态') 