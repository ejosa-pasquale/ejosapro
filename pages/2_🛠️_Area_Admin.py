import streamlit as st
import pandas as pd
import io

from utils.auth import require_code
from utils.store import save_leads_xlsx, load_leads_xlsx, validate_leads_df, REQUIRED_COLUMNS, load_bookings
from utils.pdf_ingest import parse_many_pdfs
from utils.notify import can_send_email, send_leads_digest


def _df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()

st.set_page_config(page_title="Admin", layout="wide")
st.header("🛠️ Area Admin")

if not require_code("admin"):
    st.stop()

st.subheader("Carica Excel dei lead")

st.markdown("### Carica PDF (preventivi) → aggiorna automaticamente i lead")
pdfs = st.file_uploader("Carica PDF (.pdf)", type=["pdf"], accept_multiple_files=True)
if pdfs:
    with st.spinner("Analizzo i PDF e aggiorno i lead..."):
        files = [(f.name, f.getvalue()) for f in pdfs]
        rows = parse_many_pdfs(files)
        df_new = pd.DataFrame(rows)

        ok, _, df_new = validate_leads_df(df_new)
        df_new.columns = [c.lower() for c in df_new.columns]
        for c in REQUIRED_COLUMNS:
            if c not in df_new.columns:
                df_new[c] = ""

        df_old = load_leads_xlsx().copy()
        df_old.columns = [c.lower() for c in df_old.columns]
        for c in REQUIRED_COLUMNS:
            if c not in df_old.columns:
                df_old[c] = ""

        df_merged = pd.concat([df_old, df_new], ignore_index=True)
        df_merged["lead_id"] = df_merged["lead_id"].astype(str).str.strip()
        df_merged = df_merged.drop_duplicates(subset=["lead_id"], keep="last")
        save_leads_xlsx(df_merged[REQUIRED_COLUMNS])

    st.success(f"Import PDF completato: {len(df_new)} lead letti, totale lead ora: {len(df_merged)}")
    st.dataframe(df_new[REQUIRED_COLUMNS], use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Scarica Excel aggiornato (leads_latest.xlsx)",
        data=_df_to_xlsx_bytes(df_merged[REQUIRED_COLUMNS]),
        file_name="leads_latest.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()
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
    st.success("Excel salvato. Gli installatori vedranno i lead.")
    st.dataframe(df_norm, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Ultimo Excel caricato")
df_current = load_leads_xlsx()
if df_current.empty:
    st.info("Nessun Excel caricato ancora.")
else:
    st.dataframe(df_current, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Prenotazioni")
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
st.subheader("Invio email (opzionale)")

st.write("Puoi inviare un riepilogo dei lead via email. Verrà inviato a **info@evfieldservice.it** e (se impostata) a `ADMIN_NOTIFY_EMAIL`.")
if can_send_email() and not df_current.empty:
    if st.button("✉️ Invia email con tutti i lead"):
        # Costruisci digest semplice
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
    st.info("Per inviare email imposta SMTP nei Secrets e carica almeno un Excel.")

st.caption("Nota: su Streamlit Cloud, i file caricati e le prenotazioni possono perdersi se l'app viene riavviata. Tieni sempre una copia locale dell'Excel e scarica ogni tanto bookings.csv.")
