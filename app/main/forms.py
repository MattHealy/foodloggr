from flask import g, current_app
from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, PasswordField, SubmitField, HiddenField
from wtforms.fields.html5 import EmailField
from wtforms.validators import Required, Email
from ..models import User

class LoginForm(Form):
    email = EmailField('email', validators=[Required(), Email()])
    password = PasswordField('password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class RegisterForm(Form):
    email = EmailField('email', validators=[Required(), Email()])
    password = PasswordField('password', validators=[Required()])
    password2 = PasswordField('password2', validators=[Required()])
    first_name = TextField('first_name')
    last_name = TextField('last_name')
    submit = SubmitField('Register')

    def validate(self):

        rv = Form.validate(self)

        if not rv:
            return False

        if self.password.data != self.password2.data:
            self.password.errors.append('Your passwords do not match.')
            return False

        existing_user = User.query.filter(User.email == self.email.data).filter(User.password_hash != None).first()

        if existing_user is not None:
            self.email.errors.append('This email address is already used - please choose another.')
            return False

        return True

class ForgotForm(Form):
    email = EmailField('email', validators=[Required(), Email()])
    submit = SubmitField('Reset password')

class ResetForm(Form):
    token = HiddenField('token')
    password = PasswordField('password', validators=[Required()])
    password2 = PasswordField('password2', validators=[Required()])
    submit = SubmitField('Reset password')

    def validate(self):

        rv = Form.validate(self)

        if not rv:
            return False

        if self.password.data != self.password2.data:
            self.password.errors.append('Your passwords do not match.')
            return False

        return True
