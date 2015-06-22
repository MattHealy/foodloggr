from flask import render_template, flash, redirect, url_for, request, g, current_app, session
from flask.ext.login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta
from . import main
from .forms import LoginForm, RegisterForm, EntryForm, LinkForm
from .. import db, lm
from ..models import User, Entry

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
def home():

    form = EntryForm()

    if form.validate_on_submit():
        entry = Entry(body=form.body.data, timestamp=datetime.utcnow(), user_id=g.user.id)
        db.session.add(entry)
        db.session.commit()
        #flash('Entry added.')
        return redirect(url_for('main.home'))

    entries = g.user.entries.order_by(Entry.timestamp.desc())

    return render_template("home.html", form=form, entries=entries)

@main.route('/link', methods=['GET'])
def link():
    form = LinkForm()
    return render_template("link.html", form=form)

@main.route('/register', methods=['GET','POST'])
def register():

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('main.home'))

    form = RegisterForm()

    if form.validate_on_submit():
        user = User(email=form.email.data, first_name=form.first_name.data, last_name=form.last_name.data, first_login=datetime.utcnow(), password=form.password.data)
        user.last_seen = datetime.utcnow()
        user.last_login = datetime.utcnow()
        db.session.add(user)
        db.session.commit()
        login_user(user, True)
        #flash('You have successfully registered.')
        return redirect(url_for('main.home'))

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
def logout():
    #flash('You have successfully logged out')
    logout_user()
    return redirect(url_for('main.index'))

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))
