import streamlit as st
import plotly.express as px
from streamlit_plotly_events import plotly_events
from pathlib import Path

from utils.auth import require_code
from utils.store import load_leads_xlsx, load_geojson, is_lead_booked, append_booking
from utils.notify import can_send_email, send_booking_notifications

st.set_page_config(page_title="Installatori", layout="wide")
st.header("📍 Area Installatori")

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

df = load_leads_xlsx()
df = df.copy()
df.columns = [c.lower() for c in df.columns]

required = {"lead_id","regione","citta","metri_mq","tipologia","budget_eur"}
if not required.issubset(set(df.columns)):
    st.error("Non trovo un Excel valido. Vai in **🛠️ Area Admin** e carica l'Excel usando il template.")
    st.stop()

df["lead_id"] = df["lead_id"].astype(str).str.strip()
df["regione"] = df["regione"].astype(str).str.strip()

if hide_booked:
    df = df[~df["lead_id"].apply(is_lead_booked)]

if df.empty:
    st.info("Nessun lead disponibile (o sono tutti prenotati).")
    st.stop()

geojson = load_geojson(Path("data/italy_regions.geojson"))
counts = df.groupby("regione", as_index=False).size().rename(columns={"size":"lead_count"})

st.subheader("Mappa Italia (clicca una regione)")
fig = px.choropleth(
    counts,
    geojson=geojson,
    featureidkey="properties.reg_name",
    locations="regione",
    color="lead_count",
    scope="europe",
    fitbounds="locations",
    labels={"lead_count":"Lead"},
)
fig.update_geos(visible=False)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

selected = plotly_events(fig, click_event=True, hover_event=False, select_event=False, override_height=520, override_width="100%")

selected_region = st.session_state.get("selected_region")
if selected and len(selected) > 0:
    loc = selected[0].get("location")
    if loc:
        selected_region = loc
        st.session_state["selected_region"] = selected_region

if not selected_region:
    selected_region = counts.sort_values("lead_count", ascending=False).iloc[0]["regione"]
    st.session_state["selected_region"] = selected_region

st.divider()
st.subheader(f"Lead in: {selected_region}")

sub = df[df["regione"] == selected_region].copy()
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
        subj = f"[Lead prenotato] {lead_id} - {selected_region}"
        body = (
            f"Lead: {lead_id}\n"
            f"Regione: {selected_region}\n"
            f"Città: {lead_row.get('citta','')}\n"
            f"Tipologia: {lead_row.get('tipologia','')}\n"
            f"Budget: {lead_row.get('budget_eur','')}\n\n"
            f"Installatore: {installer_name}\n"
            f"Email: {installer_email}\n"
            f"Telefono: {installer_phone}\n\n"
            f"Nota: {note}\n"
        )
        try:
            send_booking_notifications(subj, body, requester_email=installer_email)
        except Exception:
            pass

    st.success("Prenotazione registrata! L'admin la vede in 🛠️ Area Admin.")
    st.rerun()
