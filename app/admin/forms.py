from flask import g, current_app
from flask.ext.wtf import Form
from wtforms import TextField, SubmitField, HiddenField
from wtforms.validators import Required, Email
from flask_wtf.file import FileField, FileAllowed

class EntryForm(Form):
    body = TextField('body', validators=[Required()])
    entry_date = HiddenField('entry_date')
    submit = SubmitField('Add')

class RemoveEntryForm(Form):
    entry_date = HiddenField('entry_date')

class LinkForm(Form):
    email = TextField('email', validators=[Required(), Email()])
    submit = SubmitField('Send Invitation')

class ProfileForm(Form):
    first_name = TextField('first_name', validators=[Required()])
    last_name = TextField('last_name', validators=[Required()])
    email = TextField('email', validators=[Required(), Email()])
    photo = FileField('Your photo', validators=[FileAllowed(['jpg','jpeg','png','gif'], 'Images only!')])
