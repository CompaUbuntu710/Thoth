import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
IMAP_HOST = os.getenv("IMAP_HOST", "")
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASS = os.getenv("IMAP_PASS", "")


def handle_email(action, to=None, subject="", body="", mailbox="INBOX", limit=5):
    try:
        if action == "send":
            return _send_email(to, subject, body)
        elif action == "list":
            return _list_emails(mailbox, limit)
        elif action == "status":
            return _status()
        else:
            return "[Error: acción no válida. Usa: send, list, status]"
    except Exception as e:
        return f"[Error en email: {e}]"


def _send_email(to, subject, body):
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, to]):
        return "[Error: SMTP no configurado. Define SMTP_HOST, SMTP_USER, SMTP_PASS en .env]"
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    return f"[Email enviado a {to}: '{subject}']"


def _list_emails(mailbox, limit):
    if not all([IMAP_HOST, IMAP_USER, IMAP_PASS]):
        return "[Error: IMAP no configurado. Define IMAP_HOST, IMAP_USER, IMAP_PASS en .env]"
    lines = []
    with imaplib.IMAP4_SSL(IMAP_HOST) as conn:
        conn.login(IMAP_USER, IMAP_PASS)
        conn.select(mailbox)
        _, data = conn.search(None, "ALL")
        ids = data[0].split()[-limit:] if data[0] else []
        for mid in ids:
            _, msg_data = conn.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    lines.append(f"  [{mid.decode()}] {msg['Date']} - {msg['From']}: {msg['Subject']}")
    if not lines:
        return f"[Buzón '{mailbox}' vacío]"
    return "Emails:\n" + "\n".join(lines)


def _status():
    smtp_ok = bool(SMTP_HOST and SMTP_USER and SMTP_PASS)
    imap_ok = bool(IMAP_HOST and IMAP_USER and IMAP_PASS)
    return f"Email: SMTP {'✓' if smtp_ok else '✗'}, IMAP {'✓' if imap_ok else '✗'}"

