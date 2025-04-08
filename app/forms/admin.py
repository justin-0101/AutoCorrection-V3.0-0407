from flask_wtf import FlaskForm
from wtforms import IntegerField, HiddenField
from wtforms.validators import DataRequired, NumberRange

class UpdateUserCorrectionsForm(FlaskForm):
    """用户批改次数更新表单"""
    user_id = HiddenField('用户ID', 
        validators=[DataRequired(message='用户ID不能为空')])
    monthly_limit = IntegerField('每月限制', 
        validators=[
            DataRequired(message='请输入每月批改限制次数'),
            NumberRange(min=0, message='批改次数不能小于0')
        ])
    monthly_used = IntegerField('已使用次数', 
        validators=[
            DataRequired(message='请输入已使用次数'),
            NumberRange(min=0, message='已使用次数不能小于0')
        ]) 