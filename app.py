import streamlit as st

st.set_page_config(page_title="e-josa Lead Booking", layout="wide")

st.title("e-josa — Lead Booking (Excel + prenotazione)")

st.markdown(
    """**Come funziona:**
- Tu carichi un **Excel** (ogni giorno) con i lead.
- Gli installatori cliccano una **regione** e fanno **Prenota** (booking).
- Quando prenotano, parte una mail **all’installatore** e a **info@evfieldservice.it** (se SMTP è impostato).

Apri una pagina dal menu a sinistra.
"""
)

st.info("Suggerimento: prima vai su **➕ Inserisci Lead (Admin)** e carica il template compilato.")
