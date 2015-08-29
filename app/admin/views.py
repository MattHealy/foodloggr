from flask import render_template, flash, redirect, url_for, request, g, current_app, session, abort, send_from_directory
from flask.ext.login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta, date
from itsdangerous import JSONWebSignatureSerializer
from . import admin
from .forms import EntryForm, LinkForm, RemoveEntryForm, ProfileForm, AccountForm
from .. import db, lm
from ..models import User, Entry, Friendship, Vote
from ..email import send_email
from .tools import local_upload

@admin.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated():
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()

@admin.route('/home', methods=['GET','POST'])
@login_required
def home():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    form = EntryForm()
    removeform = RemoveEntryForm()

    if form.validate_on_submit():

        entry_date = None

        if form.entry_date.data.strip():
            entry_date = datetime.strptime(form.entry_date.data.strip(), "%d-%m-%Y").date()
        else:
            entry_date = date.today()

        entry = Entry(body=form.body.data.strip(), entry_date=entry_date, timestamp=datetime.utcnow(), user_id=g.user.id)

        db.session.add(entry)
        db.session.commit()

        return redirect(url_for('admin.home', date = form.entry_date.data.strip()))

    diary_date = request.args.get('date')
    placeholder = None

    if diary_date:
        try:
            today = datetime.strptime(diary_date, "%d-%m-%Y").date()
            realtoday = date.today()
            realtomorrow = realtoday + timedelta(days=1)
            realyesterday = realtoday - timedelta(days=1)
            datestring = today.strftime("%e %b")

            if today == realtoday:
                datestring = 'Today'
            elif today == realtomorrow:
                datestring = 'Tomorrow'
            elif today == realyesterday:
                datestring = 'Yesterday'

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

    return render_template("admin/home.html", form=form, removeform=removeform, entries=entries, \
                            title='News Feed', datestring = datestring, \
                            placeholder = placeholder, yesterday = yesterday, \
                            tomorrow = tomorrow)

@admin.route('/user/<int:user_id>/feed', methods=['GET'])
@login_required
def user_feed(user_id):

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    user = None
    if user_id == g.user.id:
        user = g.user
    else:
        user = User.query.join(Friendship, (Friendship.friend_id == user_id)). \
                 filter(Friendship.user_id == g.user.id). \
                 filter(User.id == user_id). \
                 filter(Friendship.confirmed == True).first_or_404()

    tomorrow = datetime.today() + timedelta(days=1)
    entries = user.entries.filter(Entry.entry_date < tomorrow).order_by(Entry.timestamp.desc()).limit(50)

    removeform = RemoveEntryForm()

    session['next_url'] = url_for('admin.user_feed', user_id = user.id)

    return render_template("admin/userfeed.html", entries=entries, user=user, showtimestamp=True, removeform=removeform)

@admin.route('/entry/<int:id>/remove', methods=['POST'])
@login_required
def remove_entry(id):

    form = RemoveEntryForm()

    if form.validate_on_submit():

        entry = Entry.query.filter(Entry.id == id, Entry.user_id == g.user.id).first_or_404()
        db.session.delete(entry)
        db.session.commit()

        next_url = session.pop('next_url')
        if next_url:
            return redirect(next_url)
        else:
            return redirect(url_for('admin.home', date = form.entry_date.data.strip()))

    else:
        return redirect(url_for('admin.home'))

@admin.route('/vote', methods=['POST'])
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

@admin.route('/uploads/<filename>')
@login_required
def show_upload(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'],filename)

@admin.route('/friend/<int:id>/remove', methods=['POST'])
@login_required
def unlink(id):

    friend = User.query.get(id)

    if friend is None:
        flash('User not found') 
    if friend == g.user:
        flash('You cannot unlink yourself.') 
        return redirect(url_for('admin.friends'))

    user = g.user.unlink(friend)

    if user is None:
        flash('Cannot unlink ' + friend.first_name)
        return redirect('admin.friends')

    db.session.add(user)
    db.session.commit()

    flash('Successfully unfriended ' + friend.first_name + ' ' + friend.last_name)
    return redirect(url_for('admin.friends'))

@admin.route('/unconfirmed', methods=['GET'])
@login_required
def unconfirmed():

    if g.user.is_confirmed():
        return redirect(url_for('admin.home'))

    return render_template("admin/unconfirmed.html", title='Unconfirmed Account')

@admin.route('/confirm/<token>', methods=['GET'])
@login_required
def confirm(token):

    if g.user.is_confirmed():
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

    if user.id == g.user.id:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        flash('You have successfully confirmed your account!')
    else:
        flash('Invalid token')

    return render_template("admin/confirm.html", title='Confirm Account')

@admin.route('/accept/<token>', methods=['GET'])
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

    return redirect(url_for('admin.friends'))

@admin.route('/friends', methods=['GET','POST'])
@login_required
def friends():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    form = LinkForm()

    if form.validate_on_submit():
        friend = User.query.filter_by(email = form.email.data.strip()).first()
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
                send_email(form.email.data.strip(), g.user.first_name + ' wants to share their food diary with you!','mail/link_friend', user=g.user, friend=friend, token=token)
                flash('A friend request has been sent to ' + form.email.data.strip())
        else:

            # Add a "Ghost" account for this user
            friend = User(email=form.email.data.strip(), is_confirmed=False)
            db.session.add(friend)
            db.session.commit()

            # Create the friend request - an unconfirmed friendship
            friendship = Friendship(user_id = g.user.id, friend_id = friend.id, confirmed=False)
            db.session.add(friendship)
            db.session.commit()
            send_email(form.email.data.strip(), g.user.first_name + ' wants to share their food diary with you!','mail/invite_friend', user=g.user)
            flash('A friend request has been sent to ' + form.email.data.strip())
        return redirect(url_for('admin.friends'))

    return render_template("admin/friends.html", form=form, title='Friends')

@admin.route('/confirmation_email', methods=['GET'])
@login_required
def send_confirmation_email():

    if g.user.is_confirmed():
        return redirect(url_for('admin.home'))

    token = g.user.generate_token()

    send_email(g.user.email, 'Confirm Account','mail/confirm_account', user=g.user, token=token)

    flash("A confirmation email has been sent to " + g.user.email)
    return redirect(url_for('admin.unconfirmed'))

@admin.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@admin.route('/profile/edit', methods=['GET','POST'])
@login_required
def edit_profile():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    user = g.user

    form = ProfileForm()

    if form.validate_on_submit():

        #existing_user = User.query.filter(User.email == form.email.data.strip()).filter(User.id != g.user.id).first()

        #if existing_user is not None:
        #    form.email.errors.append('This email address is already used - please choose another.')
        #    return False

        user.first_name = form.first_name.data.strip()
        user.last_name = form.last_name.data.strip()
        user.email = form.email.data.strip()

        if form.photo.data.filename:
            output = local_upload(form.photo)
            user.photo = output

        db.session.add(user)
        db.session.commit()

        flash('Profile updated.')

        return redirect(url_for('admin.home'))

    form.first_name.data = user.first_name
    form.last_name.data = user.last_name
    form.email.data = user.email

    return render_template("admin/edit_profile.html",title='Edit Profile',form=form)

@admin.route('/account', methods=['GET','POST'])
@login_required
def edit_account():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    user = g.user

    form = AccountForm()

    if form.validate_on_submit():

        user.password = form.password.data.strip()

        db.session.add(user)
        db.session.commit()

        flash('Account settings updated.')

        return redirect(url_for('admin.home'))

    return render_template("admin/edit_account.html",title='Edit Account',form=form)

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))
