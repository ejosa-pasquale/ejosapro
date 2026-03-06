import streamlit as st

from utils.auth import require_code
from utils.store import load_leads_xlsx, is_lead_booked, append_booking
from utils.notify import can_send_email, send_booking_notifications

st.set_page_config(page_title="Regioni", layout="wide")
st.header("🧩 Seleziona Regione — Area Installatori")

if not require_code("installer"):
    st.stop()

with st.sidebar:
    st.subheader("Dati installatore (per prenotazione)")
    installer_name = st.text_input("Nome / Azienda", value=st.session_state.get("installer_name",""))
    installer_email = st.text_input("Email", value=st.session_state.get("installer_email",""))
    installer_phone = st.text_input("Telefono", value=st.session_state.get("installer_phone",""))
    st.session_state["installer_name"] = installer_name
    st.session_state["installer_email"] = installer_email
    st.session_state["installer_phone"] = installer_phone
    hide_booked = st.checkbox("Nascondi lead già prenotati", value=True)

df = load_leads_xlsx().copy()
df.columns = [c.lower() for c in df.columns]

required = {"lead_id","regione","citta","metri_mq","tipologia","budget_eur"}
if not required.issubset(set(df.columns)):
    st.error("Non trovo un Excel valido. Vai su **➕ Inserisci Lead (Admin)** e carica l'Excel usando il template.")
    st.stop()

df["lead_id"] = df["lead_id"].astype(str).str.strip()
df["regione"] = df["regione"].astype(str).str.strip()
df["regione_key"] = df["regione"].apply(lambda x: str(x).casefold())

if hide_booked:
    df = df[~df["lead_id"].apply(is_lead_booked)]

if df.empty:
    st.info("Nessun lead disponibile (o sono tutti prenotati).")
    st.stop()

# Build region stats (case-insensitive)
agg = (
    df.groupby("regione_key", as_index=False)
      .agg(lead_count=("lead_id","count"), regione_display=("regione","first"))
      .sort_values("lead_count", ascending=False)
)

st.subheader("Scegli la tua regione")
st.caption("Clicca su un box. Mostriamo tra parentesi quanti lead disponibili ci sono.")

# Grid of region buttons
cols = st.columns(4)
selected_key = st.session_state.get("selected_region_key")

for i, row in enumerate(agg.itertuples(index=False)):
    col = cols[i % 4]
    label = f"{row.regione_display} ({int(row.lead_count)})"
    if col.button(label, use_container_width=True):
        selected_key = row.regione_key
        st.session_state["selected_region_key"] = selected_key

if not selected_key:
    selected_key = agg.iloc[0]["regione_key"]
    st.session_state["selected_region_key"] = selected_key

selected_display = agg.loc[agg["regione_key"] == selected_key, "regione_display"].iloc[0]

st.divider()
st.subheader(f"Lead disponibili in: {selected_display}")

sub = df[df["regione_key"] == selected_key].copy()
sub = sub.sort_values(by=["budget_eur","metri_mq"], ascending=[False, False], na_position="last")

cols_show = ["lead_id","citta","metri_mq","tipologia","budget_eur","note"]
for c in cols_show:
    if c not in sub.columns:
        sub[c] = ""
st.dataframe(sub[cols_show], use_container_width=True, hide_index=True)

st.markdown("### Prenota un lead")
lead_id = st.selectbox("Scegli Lead ID", options=sub["lead_id"].tolist())
lead_row = sub[sub["lead_id"] == lead_id].iloc[0].to_dict()

with st.form("book_form"):
    note = st.text_area("Nota (opzionale)")
    ok = st.form_submit_button("✅ Prenota")

if ok:
    if not installer_name or not installer_email:
        st.error("Inserisci almeno Nome/Azienda ed Email nella sidebar.")
        st.stop()
    if is_lead_booked(lead_id):
        st.warning("Questo lead risulta già prenotato. Aggiorna la pagina.")
        st.stop()

    installer = {"name": installer_name, "email": installer_email, "phone": installer_phone}
    append_booking(lead_row, installer, note=note)

    if can_send_email():
        subj = f"[Lead prenotato] {lead_id} - {selected_display}"
        body = (
            f"Lead: {lead_id}\n"
            f"Regione: {selected_display}\n"
            f"Città: {lead_row.get('citta','')}\n"
            f"Tipologia: {lead_row.get('tipologia','')}\n"
            f"Metri (mq): {lead_row.get('metri_mq','')}\n"
            f"Budget: {lead_row.get('budget_eur','')}\n\n"
            f"Installatore: {installer_name}\n"
            f"Email: {installer_email}\n"
            f"Telefono: {installer_phone}\n\n"
            f"Nota: {note}\n"
        )
        try:
            send_booking_notifications(subj, body, requester_email=installer_email)
            st.info("Email inviata a te e a info@evfieldservice.it")
        except Exception as e:
            st.error(f"Invio email fallito: {e}")

    st.success("Prenotazione registrata! L'admin la vede in ➕ Inserisci Lead (Admin).")
    st.rerun()
