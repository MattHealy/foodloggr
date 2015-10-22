from flask import render_template, flash, redirect, url_for, request, g, current_app, session, \
                  abort, send_from_directory, Response, Markup
from flask.ext.login import login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta, date
from itsdangerous import JSONWebSignatureSerializer
from . import admin
from .forms import EntryForm, LinkForm, RemoveEntryForm, ProfileForm, AccountForm, HelpForm, ReminderForm
from .. import db, lm
from ..models import User, Entry, Friendship, Vote, HelpRequest, ReminderSetting
from ..email import send_email
from ..tools import local_upload
from ..oauth import OAuthSignIn
import pytz
import json
import requests

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

    if not g.user.timezone:
        flash('Please set your timezone before you get started')
        return redirect(url_for('admin.edit_profile'))

    form = EntryForm()
    removeform = RemoveEntryForm()

    if form.validate_on_submit():

        entry_date = None

        if form.entry_date.data.strip():
            entry_date = datetime.strptime(form.entry_date.data.strip(), "%d-%m-%Y").date()
        else:
            entry_date = get_today_timezone_aware()

        entry = Entry(body=form.body.data.strip(), entry_date=entry_date, timestamp=datetime.utcnow(), user_id=g.user.id)

        db.session.add(entry)
        db.session.commit()

        if g.user.entries.count() == 1:
            message = Markup('Well done on adding your first entry!<br /><br />You can set up reminder \
                    emails so that you never forget to log your food each day.<br /><br /> \
                    <br /><strong><a href="' + url_for('admin.edit_account') + '">Click here \
                    to set up your reminders</a></strong>')
            flash(message)

        return redirect(url_for('admin.home', date = form.entry_date.data.strip()))

    diary_date = request.args.get('date')
    placeholder = None

    if diary_date:
        try:
            today = datetime.strptime(diary_date, "%d-%m-%Y").date()
            realtoday = get_today_timezone_aware()
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
            today = get_today_timezone_aware()
            datestring = 'Today'
            placeholder = today.strftime("%d-%m-%Y")
    else:
        today = get_today_timezone_aware()
        datestring = 'Today'
        placeholder = today.strftime("%d-%m-%Y")

    tomorrow = today + timedelta(days=1)

    my_entries = g.user.entries.filter(Entry.entry_date>=today).filter(Entry.entry_date<tomorrow)
    friends_entries = g.user.friends_entries(today,tomorrow)

    page = request.args.get('page', 1, type=int)

    entries = my_entries.union(friends_entries).order_by(Entry.timestamp.desc()). \
                  paginate(page, current_app.config['ENTRIES_PER_PAGE'], False)

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

    if not g.user.timezone:
        flash('Please set your timezone before you get started')
        return redirect(url_for('admin.edit_profile'))

    user = None
    if user_id == g.user.id:
        user = g.user
    else:
        user = User.query.join(Friendship, (Friendship.friend_id == user_id)). \
                 filter(Friendship.user_id == g.user.id). \
                 filter(User.id == user_id). \
                 filter(Friendship.confirmed == True).first_or_404()

    tomorrow = get_today_timezone_aware() + timedelta(days=1)

    page = request.args.get('page', 1, type=int)

    entries = user.entries.filter(Entry.entry_date < tomorrow).order_by(Entry.timestamp.desc()).paginate(page, current_app.config['ENTRIES_PER_PAGE'], False)

    removeform = RemoveEntryForm()
    removeform.redirect.data = url_for('admin.user_feed', page = page, user_id = user.id)

    return render_template("admin/userfeed.html", entries=entries, user=user, show_entry_date=True, 
                removeform=removeform)

@admin.route('/entry/<int:id>/remove', methods=['POST'])
@login_required
def remove_entry(id):

    form = RemoveEntryForm()

    if form.validate_on_submit():

        entry = Entry.query.filter(Entry.id == id, Entry.user_id == g.user.id).first_or_404()
        db.session.delete(entry)
        db.session.commit()

        if form.redirect.data:
            return redirect(form.redirect.data)
        else:
            return redirect(url_for('admin.home', date = form.entry_date.data.strip()))

    else:
        return redirect(url_for('admin.home'))

@admin.route('/vote', methods=['POST'])
@login_required
def vote():

    data = request.get_json()
    entry_id = data.get('entry_id')
    vote = data.get('vote')

    upvote = None

    if vote == 'up':
        upvote = True
    else:
        upvote = False

    entry = Entry.query.filter(Entry.id == entry_id).first_or_404()

    user = entry.user

    existing_vote = Vote.query.filter(Vote.entry_id == entry_id, Vote.upvote == upvote, Vote.from_userid == g.user.id).first()
    existing_opposite_vote = Vote.query.filter(Vote.entry_id == entry_id, Vote.upvote != upvote, Vote.from_userid == g.user.id).first()

    if existing_opposite_vote:
        existing_opposite_vote.upvote = upvote
        if upvote:
            user.score = user.score + 2
        else:
            user.score = user.score - 2
        db.session.add(existing_opposite_vote)
        db.session.add(user)
        db.session.commit()
        return '', 201

    if existing_vote:
        if upvote:
            user.score = user.score - 1
        else:
            user.score = user.score + 1
        db.session.add(user)
        db.session.delete(existing_vote)
        db.session.commit()
        return '', 204
    else:
        vote = Vote(entry_id = entry_id, from_userid = g.user.id, upvote = upvote)
        if upvote:
            user.score = user.score + 1
        else:
            user.score = user.score - 1
        db.session.add(user)
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
        friend = User.query.filter_by(email = form.email.data.strip(), confirmed = True).first()
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
            friend = User.query.filter_by(email = form.email.data.strip()).first()
            if not friend:
                friend = User(email=form.email.data.strip(), confirmed=False, score=0)

            db.session.add(friend)
            db.session.commit()

            # Create the friend request - an unconfirmed friendship
            friendship = Friendship(user_id = g.user.id, friend_id = friend.id, confirmed=False)
            db.session.add(friendship)
            db.session.commit()
            send_email(form.email.data.strip(), g.user.first_name + ' wants to share their food diary with you!','mail/invite_friend', user=g.user)
            flash('A friend request has been sent to ' + form.email.data.strip())
        return redirect(url_for('admin.friends'))

    facebook_invite_url = 'https://www.facebook.com/dialog/send?app_id=' + current_app.config['OAUTH_CREDENTIALS']['facebook']['id'] + \
         '&link=https://www.foodloggr.com' + \
         '&redirect_uri=' + url_for('admin.friends', _external=True, _scheme=current_app.config['PREFERRED_URL_SCHEME'])

    return render_template("admin/friends.html", form=form, title='Friends', facebook_invite_url=facebook_invite_url)

@admin.route('/facebookfriends', methods=['GET'])
@login_required
def facebook_friends():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    if not g.user.social_id:
        return redirect(url_for('admin.home'))

    facebook_access_token = session.get('facebook_access_token')

    if not facebook_access_token:
        session['next_url'] = url_for('admin.facebook_friends')
        return redirect(url_for('main.oauth_authorize', provider='facebook'))

    r = requests.get('https://graph.facebook.com/me/friends?access_token=' + str(facebook_access_token) + \
                     '&fields=id,name,picture')

    fbfriends = r.json()

    if fbfriends.get('error'):
        session['next_url'] = url_for('admin.facebook_friends')
        return redirect(url_for('main.oauth_authorize', provider='facebook'))

    fbfriends = fbfriends.get('data')

    facebook_invite_url = 'https://www.facebook.com/dialog/send?app_id=' + current_app.config['OAUTH_CREDENTIALS']['facebook']['id'] + \
         '&link=' + url_for('main.index', _external=True, _scheme=current_app.config['PREFERRED_URL_SCHEME']) + \
         '&redirect_uri=' + url_for('admin.friends', _external=True, _scheme=current_app.config['PREFERRED_URL_SCHEME'])

    return render_template("admin/facebook_friends.html", title='Facebook Friends', fbfriends = fbfriends, \
              facebook_invite_url = facebook_invite_url)

@admin.route('/connect_facebook', methods=['POST'])
@login_required
def connect_facebook():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    data = request.get_json()
    social_id = 'facebook$' + str(data.get('social_id'))

    friend = User.query.filter_by(social_id = social_id).first()

    if friend:
        if friend.id == g.user.id:
            return '', 400
        elif g.user.is_linked(friend):
            return '', 400
        else:
            friendship = Friendship.query.filter_by(user_id = g.user.id, friend_id = friend.id).first()
            if not friendship:
                friendship = Friendship(user_id = g.user.id, friend_id = friend.id, confirmed=False)
                db.session.add(friendship)
                db.session.commit()
            token = g.user.generate_friend_token(friend)
            send_email(friend.email, g.user.first_name + ' wants to share their food diary with you!','mail/link_friend', user=g.user, friend=friend, token=token)
            return '', 201
    else:
        return '', 400

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
        if not user.social_id:
            user.email = form.email.data.strip()
        user.timezone = form.timezone.data.strip()

        if form.photo.data:
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
    form.timezone.data = user.timezone

    return render_template("admin/edit_profile.html",title='Edit Profile',form=form)

@admin.route('/account', methods=['GET','POST'])
@login_required
def edit_account():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    user = g.user

    form = AccountForm()
    reminder_form = ReminderForm()

    if form.validate_on_submit():

        user.password = form.password.data.strip()

        db.session.add(user)
        db.session.commit()

        flash('Account settings updated.')

        return redirect(url_for('admin.home'))

    elif reminder_form.validate_on_submit():

        settings = user.reminder_settings

        if not settings:
            settings = ReminderSetting(user_id = user.id)
            db.session.add(settings)

        if reminder_form.reminder_morning.data:
            settings.morning = True
        if reminder_form.reminder_afternoon.data:
            settings.afternoon = True
        if reminder_form.reminder_evening.data:
            settings.evening= True

        db.session.add(user)
        db.session.commit()

        flash('Reminder settings updated.')

        return redirect(url_for('admin.home'))

    reminder_settings = user.reminder_settings
    if reminder_settings:
        reminder_form.reminder_morning.data = user.reminder_settings.morning
        reminder_form.reminder_afternoon.data = user.reminder_settings.afternoon
        reminder_form.reminder_evening.data = user.reminder_settings.evening

    return render_template("admin/edit_account.html",title='Edit Account',form=form, reminder_form=reminder_form)

@admin.route('/help', methods=['GET','POST'])
@login_required
def help():

    user = g.user

    form = HelpForm()

    if form.validate_on_submit():

        help = HelpRequest(user_id = user.id, timestamp = datetime.utcnow(), body = form.body.data.strip())
        db.session.add(help)
        db.session.commit()

        send_email(current_app.config['ADMIN_EMAIL'], 'Help Request','mail/help', user=user, body=form.body.data.strip())

        flash('Your help request has been sent. We will get back to you as soon as possible.')

        return redirect(url_for('admin.home'))

    return render_template("admin/help.html",title='Help',form=form)

@admin.route('/calendar', methods=['GET'])
@login_required
def calendar():

    if not g.user.is_confirmed():
        return redirect(url_for('admin.unconfirmed'))

    return render_template("admin/calendar.html")

@admin.route('/calendarfeed', methods=['GET'])
@login_required
def calendarfeed():

    entries = g.user.entries

    start = request.args.get('start')
    end = request.args.get('end')

    if start:
        entries = entries.filter(Entry.entry_date >= start)
    if end:
        entries = entries.filter(Entry.entry_date <= end)

    counter = {}
    entrylist = []

    for entry in entries:

        if not counter.get(entry.entry_date):
            counter[entry.entry_date] = 0

        if counter[entry.entry_date] >= 5:
            continue

        entryobject = {}
        entryobject['id'] = entry.id
        entryobject['title'] = entry.body
        entryobject['allDay'] = True
        entryobject['start'] = entry.entry_date.strftime('%Y-%m-%d')
        entryobject['end'] = entry.entry_date.strftime('%Y-%m-%d')

        counter[entry.entry_date] = counter[entry.entry_date] + 1

        entrylist.append(entryobject)

    return Response(json.dumps(entrylist),  mimetype='application/json')

@admin.route('/entries_json', methods=['GET'])
@login_required
def entries_ajax_search():

    entries = g.user.entries

    term = request.args.get('term')

    if term:
        entries = entries.filter(Entry.body.like(term + '%'))

    entrylist = []

    for entry in entries:
        entrylist.append(entry.body)

    entrylist = sorted(set(entrylist))

    return Response(json.dumps(entrylist),  mimetype='application/json')

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

def get_today_timezone_aware():
    return datetime.now(pytz.timezone(g.user.timezone)).date()
