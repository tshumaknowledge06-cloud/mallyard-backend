import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings


def send_email(
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
):
    message = MIMEMultipart("alternative")
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject

    text_part = MIMEText(body, "plain")
    message.attach(text_part)

    if html:
        html_part = MIMEText(html, "html")
        message.attach(html_part)

    try:
        

        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to, message.as_string())
        server.quit()

        

    except Exception as e:
        print("Email sending failed:", e)
        raise e