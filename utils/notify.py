from __future__ import annotations
import smtplib
from email.message import EmailMessage
from typing import Iterable, List, Optional

from .config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_TLS, SMTP_SSL,
    ADMIN_NOTIFY_EMAIL, COMPANY_INBOX_EMAIL
)

def can_send_email() -> bool:
    return bool(SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD and COMPANY_INBOX_EMAIL)

def _normalize(to: Iterable[str]) -> List[str]:
    out: List[str] = []
    for x in to:
        if not x:
            continue
        x = str(x).strip()
        if x and x not in out:
            out.append(x)
    return out

def send_email(subject: str, body: str, to: Iterable[str], *, from_addr: Optional[str]=None) -> None:
    recipients = _normalize(to)
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST mancante.")
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError("SMTP_USER/SMTP_PASSWORD mancanti.")
    if not recipients:
        raise RuntimeError("Nessun destinatario valido.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr or SMTP_USER  # Aruba: meglio che sia la stessa casella autenticata
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    if SMTP_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=25) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25) as server:
        if SMTP_TLS:
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

def send_booking_notifications(subject: str, body: str, requester_email: str) -> None:
    # a chi prenota + a info@evfieldservice.it
    send_email(subject, body, [requester_email, COMPANY_INBOX_EMAIL])

def send_leads_digest(subject: str, body: str) -> None:
    # a info@evfieldservice.it + (opzionale) admin
    recipients = [COMPANY_INBOX_EMAIL]
    if ADMIN_NOTIFY_EMAIL:
        recipients.append(ADMIN_NOTIFY_EMAIL)
    send_email(subject, body, recipients)
