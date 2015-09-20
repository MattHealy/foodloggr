import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASEDIR = basedir
    SECRET_KEY = os.environ.get('SECRET_KEY')
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = 'foodloggr:'
    MAIL_SENDER = os.environ.get('MAIL_SENDER')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
    CSRF_ENABLED = True
    PREFERRED_URL_SCHEME = 'https'

    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')

    S3_KEY = os.environ.get('S3_KEY')
    S3_SECRET = os.environ.get('S3_SECRET')
    S3_BUCKET = 'foodlog-userphotos'
    S3_UPLOAD_DIRECTORY = '/'

    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

    ENTRIES_PER_PAGE = 30

    OAUTH_CREDENTIALS = {
        'facebook': {
           'id': '1494241210900163',
           'secret': os.environ.get('OAUTH_FACEBOOK_SECRET')
        },
        'google': {
           'id': '',
           'secret': os.environ.get('OAUTH_GOOGLE_SECRET')
        },
        'twitter': {
           'id': '',
           'secret': os.environ.get('OAUTH_TWITTER_SECRET')
        }
    }

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app-dev.db')
    DEBUG_TB_INTERCEPT_REDIRECTS= False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app-test.db')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
