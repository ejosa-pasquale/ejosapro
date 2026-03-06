import streamlit as st

st.set_page_config(page_title="e-josa Lead Booking", layout="wide")

st.title("e-josa — Lead Booking (caricamento Excel)")

st.markdown(
    """Questa versione è pensata per essere **semplicissima**:

- ogni giorno vai in **🛠️ Area Admin** e carichi un **Excel** con i lead
- gli installatori vanno in **📍 Area Installatori**, cliccano una regione e fanno **Prenota**

Nessun collegamento con e-josa.it, nessuna API esterna.
"""
)

st.info("Apri una pagina dal menu a sinistra.")
