import smtplib, ssl
from email.message import EmailMessage

# --- necessary variables ---
SMTP_HOST = "smtp-relay.brevo.com"  # your SMTP server
SMTP_PORT = 587                     # usually 587 (TLS) or 465 (SSL)
SMTP_USER = "961eab001@smtp-brevo.com"
SMTP_PASS = "pndvTWs9A4X07GUE"

FROM_EMAIL = "noreply@fedorco.dev"
TO_EMAIL = "marian.fedorco@gmail.com"

# --- compose message ---
msg = EmailMessage()
msg["Subject"] = "Your login code"
msg["From"] = FROM_EMAIL
msg["To"] = TO_EMAIL
msg.set_content(f"<img src=\"https://fedorco.dev/logo/logo.png\" style=\"width:10rem;\"><br><p>Your one-time code is: <b>132413</b><br>(valid for 5 minutes)</p>")

# --- send via TLS ---
context = ssl.create_default_context()
with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
    server.starttls(context=context)
    server.login(SMTP_USER, SMTP_PASS)
    server.send_message(msg)