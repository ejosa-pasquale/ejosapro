import os
import streamlit as st

def get_secret(key: str, default=None):
    # Streamlit Cloud: prefer st.secrets, fallback to env
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)

# Access codes
ADMIN_CODE = str(get_secret("ADMIN_CODE", "")).strip()
INSTALLER_CODE = str(get_secret("INSTALLER_CODE", "")).strip()

# Email settings (optional)
SMTP_HOST = str(get_secret("SMTP_HOST", "")).strip()
SMTP_PORT = int(get_secret("SMTP_PORT", 587) or 587)
SMTP_USER = str(get_secret("SMTP_USER", "")).strip()
SMTP_PASSWORD = str(get_secret("SMTP_PASSWORD", "")).strip()
SMTP_TLS = str(get_secret("SMTP_TLS", "true")).lower() in ("1","true","yes","y")
SMTP_SSL = str(get_secret("SMTP_SSL", "")).strip().lower() in ("1","true","yes","y")
if not SMTP_SSL and SMTP_PORT == 465:
    SMTP_SSL = True

# Default company inbox
COMPANY_INBOX_EMAIL = str(get_secret("COMPANY_INBOX_EMAIL", "info@evfieldservice.it")).strip()
# Optional admin copy
ADMIN_NOTIFY_EMAIL = str(get_secret("ADMIN_NOTIFY_EMAIL", "")).strip()
