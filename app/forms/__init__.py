"""表单模块"""

from .admin import UpdateUserCorrectionsForm
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, HiddenField
from wtforms.validators import DataRequired, Optional, Length
from flask_wtf.file import FileAllowed, FileRequired

class EssayCorrectionForm(FlaskForm):
    """作文提交表单"""
    # CSRF token 会由 Flask-WTF 自动添加 (通过 form.hidden_tag() 或 csrf_token())
    
    subject = StringField(
        '作文标题',
        validators=[
            Optional(), 
            Length(max=200, message='标题不能超过200个字符')
        ],
        render_kw={"placeholder": "请输入作文标题（选填）"}
    )
    
    file = FileField(
        '选择文件',
        validators=[
            FileRequired(message='请选择一个文件'),
            FileAllowed(['txt', 'doc', 'docx', 'pdf'], '仅支持 txt, doc, docx, pdf 文件!')
        ]
    )
    
    # Hidden field to store source type (though it might be set by JS)
    source_type = HiddenField('source_type', default='upload')

# 可以将其他表单类也定义在这里或导入进来
# from .auth_forms import LoginForm, RegistrationForm

__all__ = ['UpdateUserCorrectionsForm', 'EssayCorrectionForm'] 