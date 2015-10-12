from flask import current_app, render_template
from flask.ext.mail import Message
from . import mail
from . import celery
from .models import User
from .email import send_email

@celery.task
def reminder_email(user_id):
    with current_app.app_context():
        user = User.query.get(user_id)
        if user:
            if user.confirmed and user.entries.count() == 0:
                send_email(user.email, "Don't forget to log your food!",'mail/reminder_newuser', user=user)
