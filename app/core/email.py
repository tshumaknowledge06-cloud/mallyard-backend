import requests
from app.core.config import settings


def send_email(to: str, subject: str, body: str):
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "html": body,
            },
            timeout=10
        )

        if response.status_code not in [200, 201]:
            print("❌ Resend error:", response.text)

    except Exception as e:
        print("❌ Email sending failed:", str(e))