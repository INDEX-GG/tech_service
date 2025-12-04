import requests

from src.config import settings

EMAILJS_USER_ID = settings.EMAILJS_USER_ID
EMAILJS_SERVICE_ID = settings.EMAILJS_SERVICE_ID
EMAILJS_TEMPLATE_ID = settings.EMAILJS_TEMPLATE_ID

def send_password_reset_email(to_email: str, token: str) -> None:
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    payload = {
        "service_id": EMAILJS_SERVICE_ID,
        "template_id": EMAILJS_TEMPLATE_ID,
        "user_id": EMAILJS_USER_ID,
        "template_params": {
            "user_email": to_email,
            "reset_link": reset_link
        }
    }
    try:
        r = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json=payload,
            timeout=10
        )
        print("📤 EmailJS ответ:", r.status_code, r.text)
    except Exception as e:
        print("❌ Ошибка:", e)