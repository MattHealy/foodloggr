from flask import g, current_app
from flask.ext.wtf import Form
from wtforms import TextField, SubmitField, HiddenField, PasswordField
from wtforms.validators import Required, Email
from flask_wtf.file import FileField, FileAllowed
from ..models import User

class EntryForm(Form):
    body = TextField('body', validators=[Required()])
    entry_date = HiddenField('entry_date')
    submit = SubmitField('Add')

class RemoveEntryForm(Form):
    redirect = HiddenField('redirect')
    entry_date = HiddenField('entry_date')

class LinkForm(Form):
    email = TextField('email', validators=[Required(), Email()])
    submit = SubmitField('Send Invitation')

class ProfileForm(Form):
    first_name = TextField('first_name', validators=[Required()])
    last_name = TextField('last_name', validators=[Required()])
    email = TextField('email', validators=[Required(), Email()])
    photo = FileField('Your photo', validators=[FileAllowed(['jpg','jpeg','png','gif'], 'Images only!')])

class AccountForm(Form):
    oldpassword = PasswordField('oldpassword', validators=[Required()])
    password = PasswordField('password', validators=[Required()])
    password2 = PasswordField('password2', validators=[Required()])

    def validate(self):

        rv = Form.validate(self)

        if not rv:
            return False

        if self.password.data != self.password2.data:
            self.password.errors.append('Your passwords do not match.')
            return False

        if not g.user.verify_password(self.oldpassword.data):
            self.oldpassword.errors.append('Incorrect password.')
            return False

        return True
