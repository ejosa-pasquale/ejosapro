# e-josa — Lead Booking (Excel upload)

## Come funziona
- Admin: carica un Excel con i lead (usa il template).
- Installatori: prenotano i lead dalla mappa Italia.
- Prenotazioni: salvate in `data/bookings.csv` (scaricabile da Admin).

## Deploy su Streamlit Cloud
Main file: `app.py`

Secrets (Settings → Secrets):

```toml
ADMIN_CODE = "codice_admin"
INSTALLER_CODE = "codice_installatori"

# opzionale: email di notifica quando un lead viene prenotato
# SMTP_HOST = "smtp..."
# SMTP_PORT = "587"
# SMTP_USER = "..."
# SMTP_PASSWORD = "..."
# SMTP_TLS = "true"
# ADMIN_NOTIFY_EMAIL = "tuaemail@e-josa.it"
```

## Email automatiche (opzionale)

Se imposti SMTP, quando un installatore **prenota** un lead, l'app invia una mail:
- **a chi prenota** (email inserita dall'installatore)
- **a info@evfieldservice.it** (o all'indirizzo che imposti in `COMPANY_INBOX_EMAIL`)

Secrets esempio:

```toml
SMTP_HOST = "smtp.tuoprovider.it"
SMTP_PORT = "587"
SMTP_USER = "noreply@e-josa.it"
SMTP_PASSWORD = "..."
SMTP_TLS = "true"

# destinatario aziendale (default: info@evfieldservice.it)
COMPANY_INBOX_EMAIL = "info@evfieldservice.it"

# opzionale: copia all'admin
ADMIN_NOTIFY_EMAIL = "tuoindirizzo@e-josa.it"
```


### Esempio Aruba (Scelta B: SSL su 465)
In Streamlit Cloud → Settings → Secrets:

```toml
SMTP_HOST = "smtps.aruba.it"
SMTP_PORT = "465"
SMTP_SSL = "true"
SMTP_TLS = "false"
SMTP_USER = "info@evfieldservice.it"
SMTP_PASSWORD = "LA_PASSWORD_DELLA_CASELLA"

COMPANY_INBOX_EMAIL = "info@evfieldservice.it"
```
