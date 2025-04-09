import enum

class EssayStatus(str, enum.Enum):
    """文章状态枚举"""
    DRAFT = 'draft'           # 草稿
    PENDING = 'pending'       # 等待批改
    CORRECTING = 'correcting' # 批改中
    PROCESSING = 'correcting' # 批改中（别名，与CORRECTING相同）
    COMPLETED = 'completed'   # 已完成
    FAILED = 'failed'        # 失败
    ARCHIVED = 'archived'    # 已归档

    @classmethod
    def get_display_text(cls, status):
        """获取状态的显示文本"""
        status_text = {
            cls.DRAFT.value: '草稿',
            cls.PENDING.value: '等待批改',
            cls.CORRECTING.value: '批改中',
            cls.COMPLETED.value: '已完成',
            cls.FAILED.value: '失败',
            cls.ARCHIVED.value: '已归档'
        }
        return status_text.get(status, '未知状态') 