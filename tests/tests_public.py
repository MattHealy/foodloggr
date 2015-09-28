import unittest
from datetime import datetime
from flask import current_app, request, url_for, redirect
from app import create_app, db
from app.models import User, Entry, Vote, Friendship

class PublicTestCase(unittest.TestCase):

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

    def test_index_route(self):
        result = self.client.get(url_for('main.index'))
        self.assertEqual(result.status_code, 200) 
        self.assertIn('foodloggr', result.data)

    def test_about_route(self):
        result = self.client.get(url_for('main.about'))
        self.assertEqual(result.status_code, 200) 
        self.assertIn('foodloggr', result.data)

    def test_terms_route(self):
        result = self.client.get(url_for('main.terms'))
        self.assertEqual(result.status_code, 200) 
        self.assertIn('foodloggr', result.data)

    def test_register_route(self):
        result = self.client.get(url_for('main.register'))
        self.assertEqual(result.status_code, 200) 
        self.assertIn('foodloggr', result.data)

    def test_login_route(self):
        result = self.client.get(url_for('main.login'))
        self.assertEqual(result.status_code, 200) 
        self.assertIn('foodloggr', result.data)

    def test_authorize_route(self):
        result = self.client.get(url_for('main.oauth_authorize', provider='facebook'))
        self.assertEqual(result.status_code, 302) 

    def test_callback_route(self):
        result = self.client.get(url_for('main.oauth_callback', provider='facebook'))
        self.assertEqual(result.status_code, 302) 

    def test_forgot_route(self):
        result = self.client.get(url_for('main.forgot'))
        self.assertEqual(result.status_code, 200) 
        self.assertIn('foodloggr', result.data)

    def test_reset_route(self):
        result = self.client.get(url_for('main.reset_password', token='test'))
        self.assertEqual(result.status_code, 404) 
        self.assertIn('foodloggr', result.data)

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
