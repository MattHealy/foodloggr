import os
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.mail import Mail
from flask.ext.moment import Moment
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CsrfProtect
from celery import Celery
from opbeat.contrib.flask import Opbeat

from werkzeug.contrib.fixers import ProxyFix

from config import config, Config

toolbar = DebugToolbarExtension()
db = SQLAlchemy()
bootstrap = Bootstrap()

lm = LoginManager()
lm.login_view = 'main.login'

mail = Mail()
moment = Moment()

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

csrf = CsrfProtect()

opbeat = Opbeat(
    organization_id = Config.OPBEAT_CREDENTIALS.get('organization_id'),
    app_id = Config.OPBEAT_CREDENTIALS.get('app_id'),
    secret_token = Config.OPBEAT_CREDENTIALS.get('secret_token')
)

def create_app(config_name):

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    lm.init_app(app)
    toolbar.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)

    csrf.init_app(app)
    opbeat.init_app(app)

    celery.conf.update(app.config)

    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/app')

    app.wsgi_app = ProxyFix(app.wsgi_app)

    @app.template_filter()
    def javascript_date(value):
        year = value.strftime('%Y')
        month = int(value.strftime('%-m')) - 1
        day = value.strftime('%-d')
        return "{0}, {1}, {2}".format(year,month,day)

    app.jinja_env.filters['javascript_date'] = javascript_date

    if not app.debug:

        import logging
        from logging.handlers import RotatingFileHandler, SMTPHandler

        file_handler = RotatingFileHandler('tmp/app.log', 'a', 1 * 1024 * 1024, 10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        app.logger.setLevel(logging.INFO)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.info('app startup')

    return app
