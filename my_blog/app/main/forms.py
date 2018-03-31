from flask_wtf import Form, FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, FileField
from wtforms.validators import Required, Length, DataRequired, Email


class CommentForm(FlaskForm):
    body = TextAreaField(' |´・ω・)ノ还不快点说点什么呀poi~', validators=[DataRequired()])
    name = StringField('昵称', validators=[DataRequired()])
    email = StringField('邮箱', validators=[Email()])
    submit = SubmitField('发表评论')
