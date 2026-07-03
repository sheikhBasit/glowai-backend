import os
import smtplib
from email.message import EmailMessage

# Mirrors the SMTP setup in the recruiter project (AI_recruiter/app/services/email.py) —
# same env var names, same 465=SSL / other=STARTTLS switch — so existing Gmail
# credentials can be copied over as-is.


def _send(to: str, subject: str, body: str) -> None:
    user = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    if not user or not password:
        # No SMTP configured on this environment — log instead of failing the request.
        print(f"[email:console] SMTP not configured — would send to {to}:\n{subject}\n{body}")
        return

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.starttls()
    with server:
        server.login(user, password)
        server.send_message(msg)


def send_password_reset_code(to_email: str, code: str) -> None:
    subject = "Your GlowGirl AI password reset code"
    body = (
        f"Your password reset code is: {code}\n\n"
        "This code expires in 15 minutes. If you didn't request a password reset, you can ignore this email."
    )
    _send(to_email, subject, body)
