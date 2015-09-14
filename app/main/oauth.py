from rauth import OAuth1Service, OAuth2Service
from flask import current_app, url_for, request, redirect, session
import json

class OAuthSignIn(object):

    providers = None

    def __init__(self, provider_name):
        self.provider_name = provider_name
        credentials = current_app.config['OAUTH_CREDENTIALS'][provider_name]
        self.consumer_id = credentials['id']
        self.consumer_secret = credentials['secret']

    def authorize(self):
        pass

    def callback(self):
        pass

    def get_callback_url(self):
        return url_for('main.oauth_callback', provider=self.provider_name,
                       _external=True, _scheme=current_app.config['PREFERRED_URL_SCHEME'])

    @classmethod
    def get_provider(self, provider_name):
        if self.providers is None:
            self.providers = {}
            for provider_class in self.__subclasses__():
                provider = provider_class()
                self.providers[provider.provider_name] = provider
        return self.providers[provider_name]

class FacebookSignIn(OAuthSignIn):
    def __init__(self):
        super(FacebookSignIn, self).__init__('facebook')
        self.service = OAuth2Service(
            name='facebook',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            authorize_url='https://graph.facebook.com/oauth/authorize',           
            access_token_url='https://graph.facebook.com/oauth/access_token',
            base_url='https://graph.facebook.com/'
        )
    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='email',
            response_type='code',
            redirect_uri=self.get_callback_url())
        )
    def callback(self):
        if 'code' not in request.args:
            return None, None, None, None
        oauth_session = self.service.get_auth_session(
            data={'code': request.args['code'],
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.get_callback_url()}
        )
        me = oauth_session.get('me?fields=email,first_name,last_name').json()

        photo_url = 'http://graph.facebook.com/' + str(me['id']) + '/picture?type=large'

        return (
            'facebook$' + me['id'],
            me.get('email'),
            me.get('first_name'),
            me.get('last_name'),
            photo_url
        )

class GoogleSignIn(OAuthSignIn):
    def __init__(self):
        super(GoogleSignIn, self).__init__('google')
        self.service = OAuth2Service(
            name='google',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            base_url='https://www.googleapis.com/oauth2/v1/',
            access_token_url='https://accounts.google.com/o/oauth2/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth'
        )
    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='openid email',
            response_type='code',
            redirect_uri=self.get_callback_url())
        )
    def callback(self):
        if 'code' not in request.args:
            return None, None, None
        oauth_session = self.service.get_auth_session(
            data=dict(
                   code=request.args['code'],
                   grant_type='authorization_code',
                   redirect_uri=self.get_callback_url()
            ),
            decoder=json.loads
        )
        me = oauth_session.get('userinfo').json()

        return (
            'google$' + me['id'],
            me.get('email'),
            me.get('given_name'),
            me.get('family_name'),
            None
        )

class TwitterSignIn(OAuthSignIn):
    def __init__(self):
        super(TwitterSignIn, self).__init__('twitter')
        self.service = OAuth1Service(
            name='twitter',
            consumer_key=self.consumer_id,
            consumer_secret=self.consumer_secret,
            request_token_url='https://api.twitter.com/oauth/request_token',
            authorize_url='https://api.twitter.com/oauth/authorize',
            access_token_url='https://api.twitter.com/oauth/access_token',
            base_url='https://api.twitter.com/1.1/'
        )
    def authorize(self):
        request_token = self.service.get_request_token(
            params={'oauth_callback': self.get_callback_url()}
        )
        session['request_token'] = request_token
        return redirect(self.service.get_authorize_url(request_token[0]))
    def callback(self):
        request_token = session.pop('request_token')
        if 'oauth_verifier' not in request.args:
            return None, None, None, None
        oauth_session = self.service.get_auth_session(
            request_token[0],
            request_token[1],
            data={'oauth_verifier': request.args['oauth_verifier']}
        )
        me = oauth_session.get('account/verify_credentials.json').json()

        social_id = 'twitter$' + str(me.get('id'))

        name = me.get('name')
        first_name = None
        last_name = None

        if ' ' in name:
            first_name, last_name = name.split()
        else:
            first_name = name

        return social_id, None, first_name, last_name, None # Twitter does not provide email
