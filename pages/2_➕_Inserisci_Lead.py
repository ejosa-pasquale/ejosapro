import streamlit as st
import pandas as pd

from utils.auth import require_code
from utils.store import save_leads_xlsx, load_leads_xlsx, validate_leads_df, REQUIRED_COLUMNS, load_bookings
from utils.notify import can_send_email, send_leads_digest

st.set_page_config(page_title="Inserisci Lead (Admin)", layout="wide")
st.header("➕ Inserisci Lead (Admin)")

if not require_code("admin"):
    st.stop()

st.subheader("1) Carica Excel dei lead (aggiornamento giornaliero)")
st.write("Scarica il template, compila e ricaricalo. Colonne minime: **lead_id, regione, citta, metri_mq, tipologia, budget_eur**.")

with open("templates/leads_template.xlsx", "rb") as f:
    st.download_button("📥 Scarica template Excel", data=f, file_name="leads_template.xlsx")

uploaded = st.file_uploader("Carica Excel (.xlsx)", type=["xlsx"])

if uploaded is not None:
    try:
        df = pd.read_excel(uploaded)
    except Exception:
        st.error("File non leggibile. Assicurati sia un .xlsx valido.")
        st.stop()

    ok, missing, df_norm = validate_leads_df(df)
    if not ok:
        st.error("Mancano colonne obbligatorie: " + ", ".join(missing))
        st.stop()

    df_norm.columns = [c.lower() for c in df_norm.columns]
    for c in REQUIRED_COLUMNS:
        if c not in df_norm.columns:
            df_norm[c] = ""
    save_leads_xlsx(df_norm)
    st.success("Excel salvato. Gli installatori vedranno subito i lead.")
    st.dataframe(df_norm, use_container_width=True, hide_index=True)

st.divider()
st.subheader("2) Ultimo Excel caricato")
df_current = load_leads_xlsx()
if df_current.empty:
    st.info("Nessun Excel caricato ancora.")
else:
    st.dataframe(df_current, use_container_width=True, hide_index=True)

st.divider()
st.subheader("3) Prenotazioni (booking)")
bookings = load_bookings()
if bookings.empty:
    st.info("Nessuna prenotazione ancora.")
else:
    st.dataframe(bookings.sort_values("booked_at", ascending=False), use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Scarica prenotazioni (CSV)",
        data=bookings.to_csv(index=False).encode("utf-8"),
        file_name="bookings.csv",
        mime="text/csv"
    )

st.divider()
st.subheader("4) Email con tutti i lead (opzionale)")
st.write("Invia un riepilogo a **info@evfieldservice.it** (e opzionalmente a `ADMIN_NOTIFY_EMAIL`).")
if can_send_email() and not df_current.empty:
    if st.button("✉️ Invia email riepilogo lead"):
        cols = [c for c in ["lead_id","regione","citta","metri_mq","tipologia","budget_eur"] if c in df_current.columns]
        digest_df = df_current[cols].copy()
        lines = ["Riepilogo lead (ultimo Excel caricato):", ""]
        for _, row in digest_df.iterrows():
            parts = [f"{col}: {row.get(col,'')}" for col in cols]
            lines.append(" - " + " | ".join(parts))
        body = "\n".join(lines)
        try:
            send_leads_digest("Riepilogo lead e-josa (Excel)", body)
            st.success("Email inviata.")
        except Exception:
            st.error("Invio email fallito. Controlla SMTP nei Secrets.")
else:
    st.info("Per inviare email: imposta SMTP nei Secrets e carica almeno un Excel.")

st.caption("Nota: su Streamlit Cloud i file in `data/` possono sparire se l’app viene riavviata. Tieni sempre una copia dell’Excel e scarica periodicamente bookings.csv.")
