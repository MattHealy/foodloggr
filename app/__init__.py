import os
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager


from werkzeug.contrib.fixers import ProxyFix

from config import config

toolbar = DebugToolbarExtension()
db = SQLAlchemy()

lm = LoginManager()
lm.login_view = 'main.login'


def create_app(config_name):

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    lm.init_app(app)
    toolbar.init_app(app)

    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    app.wsgi_app = ProxyFix(app.wsgi_app)

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
