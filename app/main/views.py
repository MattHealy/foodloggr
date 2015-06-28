from flask import render_template, flash, redirect, url_for, request, g, current_app, session, abort
from flask.ext.login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta
from itsdangerous import JSONWebSignatureSerializer
from . import main
from .forms import LoginForm, RegisterForm, EntryForm, LinkForm
from .. import db, lm
from ..models import User, Entry
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

@main.route('/home', methods=['GET','POST'])
@login_required
def home():

    if not g.user.is_confirmed():
        return redirect(url_for('main.unconfirmed'))

    form = EntryForm()

    if form.validate_on_submit():
        entry = Entry(body=form.body.data, timestamp=datetime.utcnow(), user_id=g.user.id)
        db.session.add(entry)
        db.session.commit()
        #flash('Entry added.')
        return redirect(url_for('main.home'))

    entries = g.user.entries.order_by(Entry.timestamp.desc())

    return render_template("home.html", form=form, entries=entries, title='Dashboard')

@main.route('/entry/<int:id>/remove', methods=['POST'])
@login_required
def remove_entry(id):
    entry = Entry.query.filter(Entry.id == id, Entry.user_id == g.user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('main.home'))

@main.route('/unconfirmed', methods=['GET'])
@login_required
def unconfirmed():

    if g.user.is_confirmed():
        return redirect(url_for('main.home'))

    return render_template("unconfirmed.html", title='Unconfirmed Account')

@main.route('/confirm/<token>', methods=['GET'])
@login_required
def confirm(token):

    if g.user.is_confirmed():
        return redirect(url_for('main.home'))

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

    if user.id == g.user.id:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        flash('You have successfully confirmed your account!')
    else:
        flash('Invalid token')

    return render_template("confirm.html", title='Confirm Account')

@main.route('/link', methods=['GET'])
@login_required
def link():

    if not g.user.is_confirmed():
        return redirect(url_for('main.unconfirmed'))

    form = LinkForm()
    return render_template("link.html", form=form, title='Friends')

@main.route('/confirmation_email', methods=['GET'])
@login_required
def send_confirmation_email():

    if g.user.is_confirmed():
        return redirect(url_for('main.home'))

    token = g.user.generate_token()

    send_email(g.user.email, 'Confirm Account','mail/confirm_account', user=g.user, token=token)

    flash("A confirmation email has been sent to " + g.user.email)
    return redirect(url_for('main.unconfirmed'))

@main.route('/register', methods=['GET','POST'])
def register():

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('main.home'))

    form = RegisterForm()

    if form.validate_on_submit():
        user = User(email=form.email.data, first_name=form.first_name.data, last_name=form.last_name.data, first_login=datetime.utcnow(), password=form.password.data, is_confirmed=False)
        user.last_seen = datetime.utcnow()
        user.last_login = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        login_user(user, True)
        token = user.generate_token()
        send_email(form.email.data, 'Confirm Account','mail/confirm_account', user=user, token=token)
        send_email(current_app.config['ADMIN_EMAIL'], 'New User','mail/new_user', user=user)
        return redirect(url_for('main.unconfirmed'))

    return render_template('register.html', title='Register', form=form)

@main.route('/login', methods=['GET','POST'])
def login():

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('main.home'))

    if request.args.get('next'):
        session['next_url'] = request.args.get('next')

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter(User.email==form.email.data).filter(User.password_hash!=None).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.home'))
        flash('Invalid username or password.')

    return render_template('login.html', title='Sign In', form=form)

@main.route('/logout')
@login_required
def logout():
    #flash('You have successfully logged out')
    logout_user()
    return redirect(url_for('main.index'))

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))
