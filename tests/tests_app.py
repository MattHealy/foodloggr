import unittest
from datetime import datetime
from flask import current_app, request, url_for, redirect
from app import create_app, db
from app.models import User, Entry, Vote, Friendship

class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.client = self.app.test_client()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])

    def login(self, email, password):
        return self.client.post(url_for('main.login'), data=dict(
           email=email,
           password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get(url_for('admin.logout'), follow_redirects=True)

    def test_login_logout(self):
        u = User(score=0, email='test@test.com', first_name='Test', last_name='User', first_login=datetime.utcnow(), password='password')
        db.session.add(u)
        u.confirmed=True
        u.timezone='Australia/Perth'
        db.session.commit()
        rv = self.login('test@test.com','password')
        self.assertNotIn('Unconfirmed', rv.data)
        self.assertIn('News Feed', rv.data)
        rv = self.logout()
        self.assertIn('Simple Food Logging', rv.data)

    def test_register(self):
        rv = self.client.post(url_for('main.register'), data=dict(
           first_name='Test',
           last_name='User',
           email='test@test.com',
           password='password',
           password2='password'
        ), follow_redirects=True)
        self.assertIn('Unconfirmed', rv.data)

    def test_add_entry(self):
        u = User(score=0, email='test@test.com', first_name='Test', last_name='User', first_login=datetime.utcnow(), password='password')
        db.session.add(u)
        u.confirmed=True
        u.timezone='Australia/Perth'
        db.session.commit()
        rv = self.login('test@test.com','password')
        rv = self.client.post(url_for('admin.home'), data=dict(
           body='Icecream'
        ), follow_redirects=True)
        self.assertIn('Icecream', rv.data)

if __name__ == '__main__':
    try:
        unittest.main()
    except:
        pass
    cov.stop()
    cov.save()
    print "\n\nCoverage Report:\n"
    cov.report()
    print "HTML version: " + os.path.join(basedir, "tmp/coverage/index.html")
    cov.html_report(directory='tmp/coverage')
    cov.erase()
