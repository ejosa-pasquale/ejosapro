from __future__ import annotations
import smtplib
from email.message import EmailMessage
from typing import Iterable, List

from .config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_TLS, SMTP_SSL,
    ADMIN_NOTIFY_EMAIL, COMPANY_INBOX_EMAIL
)

def can_send_email() -> bool:
    return bool(SMTP_HOST and (COMPANY_INBOX_EMAIL or ADMIN_NOTIFY_EMAIL))

def _normalize(to: Iterable[str]) -> List[str]:
    out: List[str] = []
    for x in to:
        if not x:
            continue
        x = str(x).strip()
        if x and x not in out:
            out.append(x)
    return out

def send_email(subject: str, body: str, to: Iterable[str]) -> None:
    recipients = _normalize(to)
    if not SMTP_HOST or not recipients:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_USER or (ADMIN_NOTIFY_EMAIL or COMPANY_INBOX_EMAIL)
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    if SMTP_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_TLS:
            server.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

def send_booking_notifications(subject: str, body: str, requester_email: str) -> None:
    # a chi prenota + a info@evfieldservice.it
    send_email(subject, body, [requester_email, COMPANY_INBOX_EMAIL])

def send_leads_digest(subject: str, body: str) -> None:
    # a info@evfieldservice.it + (opzionale) admin
    send_email(subject, body, [COMPANY_INBOX_EMAIL, ADMIN_NOTIFY_EMAIL])
