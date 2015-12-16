from flask import current_app, render_template
from flask.ext.mail import Message
from . import mail
from . import celery
from .models import User, ReminderSetting
from .email import send_email
from datetime import datetime
import pytz

@celery.task
def reminder_email(user_id):
    with current_app.app_context():
        user = User.query.get(user_id)
        if user:
            if user.confirmed and user.entries.count() == 0:
                send_email(user.email, "Don't forget to log your food!",'mail/reminder_newuser', user=user)

@celery.task
def daily_reminder_email():

    # Morning emails - 9am local time
    # Afternoon emails - 2pm local time
    # Evening emails - 8pm local time

    with current_app.app_context():
        users = User.query.join(ReminderSetting).filter(User.confirmed == True).all()
        for user in users:
            if user.timezone:
                now_hour = datetime.now(pytz.timezone(user.timezone)).hour
                if user.reminder_settings.morning and now_hour == 9:
                    send_email(user.email, "Morning reminder",'mail/reminder_daily', user=user)
                if user.reminder_settings.afternoon and now_hour == 14:
                    send_email(user.email, "Afternoon reminder",'mail/reminder_daily', user=user)
                if user.reminder_settings.evening and now_hour == 20:
                    send_email(user.email, "Evening reminder",'mail/reminder_daily', user=user)

@celery.task
def weight_reminder_email():

    with current_app.app_context():
        users = User.query.join(ReminderSetting).filter(User.confirmed == True).all()
        for user in users:
            if user.timezone:
                now_hour = datetime.now(pytz.timezone(user.timezone)).hour
                now_day = datetime.now(pytz.timezone(user.timezone)).isoweekday()
                if user.reminder_settings.weight_day == now_day and now_hour == 7:
                    send_email(user.email, "Record your weight for this week",'mail/reminder_weight', user=user)
