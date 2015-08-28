from flask import render_template, flash, redirect, url_for, request, g, current_app, session, abort
from flask.ext.login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta, date
from itsdangerous import JSONWebSignatureSerializer
from . import main
from .forms import LoginForm, RegisterForm, EntryForm, LinkForm, ResetForm, ForgotForm, RemoveEntryForm, ProfileForm
from .. import db, lm
from ..models import User, Entry, Friendship, Vote
from ..email import send_email
from .tools import local_upload

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
    removeform = RemoveEntryForm()

    if form.validate_on_submit():

        entry_date = None

        if form.entry_date.data:
            entry_date = datetime.strptime(form.entry_date.data, "%d-%m-%Y").date()
        else:
            entry_date = date.today()

        entry = Entry(body=form.body.data, entry_date=entry_date, timestamp=datetime.utcnow(), user_id=g.user.id)

        db.session.add(entry)
        db.session.commit()

        return redirect(url_for('main.home', date = form.entry_date.data))

    diary_date = request.args.get('date')
    placeholder = None

    if diary_date:
        try:
            today = datetime.strptime(diary_date, "%d-%m-%Y").date()
            realtoday = date.today()
            datestring = today.strftime("%e %b")
            if today == realtoday:
                datestring = 'Today'
            placeholder = today.strftime("%d-%m-%Y")
        except:
            today = date.today()
            datestring = 'Today'
            placeholder = today.strftime("%d-%m-%Y")
    else:
        today = date.today()
        datestring = 'Today'
        placeholder = today.strftime("%d-%m-%Y")

    tomorrow = today + timedelta(days=1)

    my_entries = g.user.entries.filter(Entry.entry_date>=today).filter(Entry.entry_date<tomorrow)
    friends_entries = g.user.friends_entries(today,tomorrow)

    entries = my_entries.union(friends_entries).order_by(Entry.timestamp.desc())

    form.entry_date.data = placeholder
    removeform.entry_date.data = placeholder

    tomorrow = tomorrow.strftime("%d-%m-%Y")
    yesterday = (today - timedelta(days=1)).strftime("%d-%m-%Y")

    return render_template("home.html", form=form, removeform=removeform, entries=entries, \
                            title='News Feed', datestring = datestring, \
                            placeholder = placeholder, yesterday = yesterday, \
                            tomorrow = tomorrow)

@main.route('/entry/<int:id>/remove', methods=['POST'])
@login_required
def remove_entry(id):

    form = RemoveEntryForm()

    if form.validate_on_submit():

        entry = Entry.query.filter(Entry.id == id, Entry.user_id == g.user.id).first_or_404()
        db.session.delete(entry)
        db.session.commit()

        return redirect(url_for('main.home', date = form.entry_date.data))

    else:
        return redirect(url_for('main.home'))

@main.route('/vote', methods=['POST'])
@login_required
def vote():

    data = request.get_json()
    entry_id = data.get('entry_id')
    upvote = data.get('upvote')

    entry = Entry.query.filter(Entry.id == entry_id).first_or_404()

    existing_vote = Vote.query.filter(Vote.entry_id == entry_id, Vote.upvote == upvote, Vote.from_userid == g.user.id).first()
    existing_opposite_vote = Vote.query.filter(Vote.entry_id == entry_id, Vote.upvote != upvote, Vote.from_userid == g.user.id).first()

    if existing_opposite_vote:
        db.session.delete(existing_opposite_vote)

    if existing_vote:
        db.session.delete(existing_vote)
        return '', 204
    else:
        vote = Vote(entry_id = entry_id, from_userid = g.user.id, upvote = upvote)
        db.session.add(vote)
        db.session.commit()
        return '', 201

@main.route('/uploads/<filename>')
def show_upload(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'],filename)

@main.route('/friend/<int:id>/remove', methods=['POST'])
@login_required
def unlink(id):

    friend = User.query.get(id)

    if friend is None:
        flash('User not found') 
    if friend == g.user:
        flash('You cannot unlink yourself.') 
        return redirect(url_for('main.link'))

    user = g.user.unlink(friend)

    if user is None:
        flash('Cannot unlink ' + friend.first_name)
        return redirect('main.link')

    db.session.add(user)
    db.session.commit()

    flash('Successfully unfriended ' + friend.first_name + ' ' + friend.last_name)
    return redirect(url_for('main.link'))

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

@main.route('/accept/<token>', methods=['GET'])
@login_required
def accept_link(token):

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

    if data.get('friend_id'):
        friend_id = data.get('friend_id')
    else:
        friend_id = 0

    user = User.query.get_or_404(friend_id)
    friend = User.query.get_or_404(id)

    if user.id == g.user.id:
        g.user.link(friend)
        db.session.add(user)
        db.session.commit()
        flash('You are now friends with ' + friend.first_name)
    else:
        flash('Invalid token')

    return redirect(url_for('main.home'))

@main.route('/link', methods=['GET','POST'])
@login_required
def link():

    if not g.user.is_confirmed():
        return redirect(url_for('main.unconfirmed'))

    form = LinkForm()

    if form.validate_on_submit():
        friend = User.query.filter_by(email = form.email.data).first()
        if friend:
            if friend.id == g.user.id:
                flash('You cannot enter your own email address here.')
            elif g.user.is_linked(friend):
                flash('You are already friends with ' + friend.first_name + '.')
            else:
                friendship = Friendship.query.filter_by(user_id = g.user.id, friend_id = friend.id).first()
                if not friendship:
                    friendship = Friendship(user_id = g.user.id, friend_id = friend.id, confirmed=False)
                    db.session.add(friendship)
                    db.session.commit()
                token = g.user.generate_friend_token(friend)
                send_email(form.email.data, g.user.first_name + ' wants to share their food diary with you!','mail/link_friend', user=g.user, friend=friend, token=token)
                flash('A friend request has been sent to ' + form.email.data)
        else:

            # Add a "Ghost" account for this user
            friend = User(email=form.email.data, is_confirmed=False)
            db.session.add(friend)
            db.session.commit()

            # Create the friend request - an unconfirmed friendship
            friendship = Friendship(user_id = g.user.id, friend_id = friend.id, confirmed=False)
            db.session.add(friendship)
            db.session.commit()
            send_email(form.email.data, g.user.first_name + ' wants to share their food diary with you!','mail/invite_friend', user=g.user)
            flash('A friend request has been sent to ' + form.email.data)
        return redirect(url_for('main.link'))

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

        user = User.query.filter(User.email == form.email.data).filter(User.password_hash == None).first()

        if user:
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.first_login = datetime.utcnow()
            user.password = form.password.data
            user.is_confirmed = False
        else:
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

@main.route('/forgot', methods=['GET','POST'])
def forgot():

    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('main.home'))

    form = ForgotForm()

    if form.validate_on_submit():
        user = User.query.filter(User.email==form.email.data).filter(User.password_hash!=None).first()
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

    form = ResetForm()

    if form.validate_on_submit():
        user.password = form.password.data
        db.session.add(user)
        db.session.commit()
        flash('Your password has now been reset.')
        return redirect(url_for('main.login'))

    return render_template('reset.html', title='Reset Password', form=form, user=user, token=token)

@main.route('/profile/edit', methods=['GET','POST'])
@login_required
def edit_profile():

    if not g.user.is_confirmed():
        return redirect(url_for('main.unconfirmed'))

    user = g.user

    form = ProfileForm()

    if form.validate_on_submit():

        #existing_user = User.query.filter(User.email == form.email.data).filter(User.id != g.user.id).first()

        #if existing_user is not None:
        #    form.email.errors.append('This email address is already used - please choose another.')
        #    return False

        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data

        if form.photo.data.filename:
            output = local_upload(form.photo)
            user.photo = output

        db.session.add(user)
        db.session.commit()

        flash('Profile updated.')

        return redirect(url_for('main.home'))

    form.first_name.data = user.first_name
    form.last_name.data = user.last_name
    form.email.data = user.email

    return render_template("edit_profile.html",title='Edit Profile',form=form)

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))
