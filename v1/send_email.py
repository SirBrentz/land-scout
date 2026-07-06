"""Send the digest via Gmail SMTP using an app password from v1/.env.

.env needs:
  GMAIL_ADDRESS=brentremow@gmail.com
  GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx   (myaccount.google.com/apppasswords)
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import load_env


def send(subject: str, html: str) -> bool:
    env = load_env()
    addr = env.get("GMAIL_ADDRESS")
    pw = env.get("GMAIL_APP_PASSWORD")
    if not addr or not pw:
        print("send_email: GMAIL_ADDRESS / GMAIL_APP_PASSWORD missing from .env — digest saved locally only")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Land Scout <{addr}>"
    msg["To"] = addr
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(addr, pw)
        s.sendmail(addr, [addr], msg.as_string())
    return True
