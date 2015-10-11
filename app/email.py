from flask import current_app, render_template
from flask.ext.mail import Message
from . import mail
from . import celery

@celery.task
def send_async_email(msg):
    with current_app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    send_async_email.delay(msg)
