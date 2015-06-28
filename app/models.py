from app import db
from flask import current_app
from itsdangerous import JSONWebSignatureSerializer
from werkzeug.security import generate_password_hash, check_password_hash

friendship = db.Table('friendship',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), unique=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(db.String(64), index = True)
    entries = db.relationship('Entry', backref='user', lazy='dynamic')
    last_seen = db.Column(db.DateTime)
    first_login = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean)
    friends = db.relationship('User', secondary=friendship,
                                      primaryjoin=(friendship.c.user_id == id),
                                      secondaryjoin=(friendship.c.friend_id == id),
                                      backref=db.backref('friendship', lazy='dynamic'),
                                      lazy='dynamic')

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

    def link(self, user):
        if not self.is_linked(user):
            self.friends.append(user)
            return self

    def unlink(self, user):
        if self.is_linked(user):
            self.friends.remove(user)
            return self

    def is_linked(self, user):
        return self.friends.filter(friendship.c.friend_id == user.id).count() > 0

    def friends_entries(self):
        return Entry.query.join(friendship, (friendship.c.friend_id == Entry.user_id)).filter(friendship.c.user_id == self.id).order_by(Entry.timestamp.desc())

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
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Entry %r>' % (self.body)

