# e-josa — Lead Booking (Excel + prenotazione + email)

## Deploy (Streamlit Cloud)
- Main file: `app.py`

### Secrets minimi
```toml
ADMIN_CODE = "codice_admin"
INSTALLER_CODE = "codice_installatori"
```

### Email Aruba (SSL 465) — Scelta B
```toml
SMTP_HOST = "smtps.aruba.it"
SMTP_PORT = "465"
SMTP_SSL = "true"
SMTP_TLS = "false"

SMTP_USER = "info@evfieldservice.it"
SMTP_PASSWORD = "LA_PASSWORD_DELLA_CASELLA"

COMPANY_INBOX_EMAIL = "info@evfieldservice.it"
# opzionale
# ADMIN_NOTIFY_EMAIL = "tuoindirizzo@e-josa.it"
```

## Uso
1) Admin: apri **➕ Inserisci Lead (Admin)** → scarica template → carica Excel compilato  
2) Installatori: aprono **📍 Mappa Italia** → scelgono regione → **Prenota**  
3) Alla prenotazione parte una mail a:
- email installatore
- info@evfieldservice.it

## Nota su persistenza
Su Streamlit Cloud i file possono sparire se l’app viene riavviata:
- conserva sempre l’Excel localmente
- scarica `bookings.csv` ogni tanto
