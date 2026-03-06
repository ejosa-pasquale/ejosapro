import os
import streamlit as st

def get_secret(key: str, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)

ADMIN_CODE = str(get_secret("ADMIN_CODE", "")).strip()
INSTALLER_CODE = str(get_secret("INSTALLER_CODE", "")).strip()

SMTP_HOST = str(get_secret("SMTP_HOST", "")).strip()
SMTP_PORT = int(get_secret("SMTP_PORT", 587) or 587)
SMTP_USER = str(get_secret("SMTP_USER", "")).strip()
SMTP_PASSWORD = str(get_secret("SMTP_PASSWORD", "")).strip()
SMTP_TLS = str(get_secret("SMTP_TLS", "true")).lower() in ("1","true","yes","y")
ADMIN_NOTIFY_EMAIL = str(get_secret("ADMIN_NOTIFY_EMAIL", "")).strip()

COMPANY_INBOX_EMAIL = str(get_secret("COMPANY_INBOX_EMAIL", "info@evfieldservice.it")).strip()


# Per Aruba: spesso si usa SSL diretto su 465 (SMTP_SSL=true, SMTP_TLS=false)
SMTP_SSL = str(get_secret("SMTP_SSL", "")).strip().lower() in ("1","true","yes","y")
if not SMTP_SSL and SMTP_PORT == 465:
    SMTP_SSL = True
