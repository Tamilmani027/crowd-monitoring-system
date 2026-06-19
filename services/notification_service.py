import json
import logging
import smtplib
from email.message import EmailMessage
from urllib import request as urlrequest

from config import Config


logger = logging.getLogger(__name__)


def send_email_alert(subject: str, body: str) -> str:
    smtp_host = getattr(Config, 'SMTP_HOST', '')
    smtp_port = int(getattr(Config, 'SMTP_PORT', 0) or 0)
    smtp_username = getattr(Config, 'SMTP_USERNAME', '')
    smtp_password = getattr(Config, 'SMTP_PASSWORD', '')
    email_to = getattr(Config, 'ALERT_EMAIL_TO', '')
    email_from = getattr(Config, 'ALERT_EMAIL_FROM', smtp_username)

    if not (smtp_host and smtp_port and smtp_username and smtp_password and email_to and email_from):
        return 'not_configured'

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = email_from
    message['To'] = email_to
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as client:
            client.starttls()
            client.login(smtp_username, smtp_password)
            client.send_message(message)
        return 'sent'
    except Exception:
        logger.exception('Failed to send email alert')
        return 'failed'


def send_webhook_alert(payload: dict) -> str:
    webhook_url = getattr(Config, 'WEBHOOK_URL', '')
    if not webhook_url:
        return 'not_configured'

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urlrequest.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
        with urlrequest.urlopen(req, timeout=10):
            return 'sent'
    except Exception:
        logger.exception('Failed to send webhook alert')
        return 'failed'
