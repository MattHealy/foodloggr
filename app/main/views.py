from flask import render_template, flash, redirect, url_for, request, g, current_app, session, abort
from flask.ext.login import login_user, current_user
from datetime import datetime
from itsdangerous import JSONWebSignatureSerializer
from . import main
from .forms import LoginForm, RegisterForm, ResetForm, ForgotForm
from .. import db, lm
from ..models import User
from ..email import send_email

@main.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated():
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()

@main.route('/', methods=['GET'])
def index():
    return render_template("index.html")

@main.route('/register', methods=['GET','POST'])
def register():

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('admin.home'))

    form = RegisterForm()

    if form.validate_on_submit():

        user = User.query.filter(User.email == form.email.data.strip()).filter(User.password_hash == None).first()

        if user:
            user.first_name = form.first_name.data.strip()
            user.last_name = form.last_name.data.strip()
            user.first_login = datetime.utcnow()
            user.password = form.password.data.strip()
            user.is_confirmed = False
        else:
            user = User(email=form.email.data.strip(), first_name=form.first_name.data.strip(), last_name=form.last_name.data.strip(), first_login=datetime.utcnow(), password=form.password.data.strip(), is_confirmed=False)

        user.last_seen = datetime.utcnow()
        user.last_login = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        login_user(user, True)
        token = user.generate_token()
        send_email(form.email.data.strip(), 'Confirm Account','mail/confirm_account', user=user, token=token)
        send_email(current_app.config['ADMIN_EMAIL'], 'New User','mail/new_user', user=user)
        return redirect(url_for('admin.unconfirmed'))

    return render_template('register.html', title='Register', form=form)

@main.route('/login', methods=['GET','POST'])
def login():

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('admin.home'))

    if request.args.get('next'):
        session['next_url'] = request.args.get('next')

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter(User.email==form.email.data.strip()).filter(User.password_hash!=None).first()
        if user is not None and user.verify_password(form.password.data.strip()):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('admin.home'))
        flash('Invalid username or password.')

    return render_template('login.html', title='Sign In', form=form)

@main.route('/forgot', methods=['GET','POST'])
def forgot():

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('admin.home'))

    form = ForgotForm()

    if form.validate_on_submit():
        user = User.query.filter(User.email==form.email.data.strip()).filter(User.password_hash!=None).first()
        if user is None:
            flash('Sorry, we could not find a user with that email address.')
        else:
            token = user.generate_token()
            send_email(user.email, 'Password Reset','mail/password_reset', user=user, token=token)
            flash('An email containing password reset instructions has been sent to ' + user.email + '.')
            return redirect(url_for('main.forgot'))

    return render_template('forgot.html', title='Forgot Your Password', form=form)

@main.route('/reset/<token>', methods=['GET','POST'])
def reset_password(token):

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('admin.home'))

    s = JSONWebSignatureSerializer(current_app.config['SECRET_KEY'])

    data = None

    try:
        data = s.loads(token)
    except:
        abort(404)

    if data.get('id'):
        id = data.get('id')
    else:
        id = 0

    user = User.query.get_or_404(id)

    form = ResetForm()

    if form.validate_on_submit():
        user.password = form.password.data.strip()
        db.session.add(user)
        db.session.commit()
        flash('Your password has now been reset.')
        return redirect(url_for('main.login'))

    return render_template('reset.html', title='Reset Password', form=form, user=user, token=token)
