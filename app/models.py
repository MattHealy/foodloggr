from app import db
from flask import current_app
from itsdangerous import JSONWebSignatureSerializer
from werkzeug.security import generate_password_hash, check_password_hash

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    confirmed = db.Column(db.Boolean)
    user = db.relationship('User', primaryjoin="Friendship.user_id == User.id")
    friend = db.relationship('User', primaryjoin="Friendship.friend_id == User.id")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), unique=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(db.String(64), index = True)
    last_seen = db.Column(db.DateTime)
    first_login = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean)

    entries = db.relationship('Entry', backref='user', lazy='dynamic')

    friends = db.relationship('Friendship',
                              primaryjoin="and_(Friendship.user_id == User.id, Friendship.confirmed == True)",
                              lazy='dynamic', 
                              foreign_keys='Friendship.user_id',
              )

    friend_requests = db.relationship('Friendship',
                              primaryjoin="and_(Friendship.friend_id == User.id, Friendship.confirmed == False)",
                              lazy='dynamic', 
                              foreign_keys='Friendship.friend_id',
              )

    def is_admin(self):
        if str(self.id) in current_app.config['ADMINS']:
            return True
        else:
            return False

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return True

    def is_confirmed(self):
        return self.confirmed

    def get_id(self):
        return unicode(self.id)

    def generate_token(self):
        s = JSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'id': self.id})

    def generate_friend_token(self, friend):
        s = JSONWebSignatureSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'id': self.id, 'friend_id': friend.id})

    def link(self, friend):
        if not self.is_linked(friend):

            friendship = Friendship.query.filter_by(user_id = self.id, friend_id = friend.id).first()
            if friendship:
                friendship.confirmed = True
            else:
                friendship =  Friendship(user_id = self.id, friend_id = friend.id, confirmed = True)

            db.session.add(friendship)
            db.session.commit()

            if not friend.is_linked(self):
                friend.link(self)

            return self

    def unlink(self, friend):
        if self.is_linked(friend):

            friendship = Friendship.query.filter_by(user_id = self.id, friend_id = friend.id)
            db.session.delete(friendship)
            db.session.commit()

            if friend.is_linked(self):
                friend.unlink(self)

            return self

    def is_linked(self, friend):
        return Friendship.query.filter_by(user_id = self.id, friend_id = friend.id, confirmed = True).count() > 0

    def friends_entries(self, today, tomorrow):
        return Entry.query.join(Friendship, (Friendship.friend_id == Entry.user_id)). \
                 filter(Friendship.user_id == self.id). \
                 filter(Entry.entry_date>=today).filter(Entry.entry_date<tomorrow). \
                 order_by(Entry.timestamp.desc())

    def __repr__(self):
        return '<User %r %r>' % (self.first_name, self.last_name)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(64))
    entry_date = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Entry %r>' % (self.body)

