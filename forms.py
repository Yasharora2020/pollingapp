from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, ValidationError, TextAreaField
from wtforms.validators import DataRequired
from wtforms import RadioField, SubmitField

class PollForm(FlaskForm):
    question = StringField('Question', validators=[DataRequired()])
    choices = TextAreaField('Choices (one choice per line)', validators=[DataRequired()])
    submit = SubmitField('Create Poll')

class VoteForm(FlaskForm):
    choice = RadioField('Choices', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Vote')
