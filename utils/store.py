from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st
import datetime as dt

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LEADS_XLSX = DATA_DIR / "leads_latest.xlsx"
BOOKINGS_CSV = DATA_DIR / "bookings.csv"

REQUIRED_COLUMNS = [
    "lead_id","data_inserimento","regione","citta","indirizzo","metri_mq","tipologia","budget_eur","note",
    "contatto_email","contatto_telefono"
]

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename_map = {
        "mq": "metri_mq",
        "metri": "metri_mq",
        "metri quadri": "metri_mq",
        "budget": "budget_eur",
        "telefono": "contatto_telefono",
        "email": "contatto_email",
    }
    return df.rename(columns=rename_map)

def validate_leads_df(df: pd.DataFrame):
    df = _normalize_columns(df)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, missing, df
    return True, [], df

@st.cache_data(show_spinner=False)
def load_geojson(path: Path) -> dict:
    import json
    return json.loads(path.read_text(encoding="utf-8"))

def save_leads_xlsx(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_excel(LEADS_XLSX, index=False)

def load_leads_xlsx() -> pd.DataFrame:
    if not LEADS_XLSX.exists():
        return pd.DataFrame(columns=REQUIRED_COLUMNS)
    df = pd.read_excel(LEADS_XLSX)
    ok, _, df2 = validate_leads_df(df)
    return df2 if ok else df

def _init_bookings_if_missing():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not BOOKINGS_CSV.exists():
        pd.DataFrame(columns=[
            "booked_at","lead_id","regione","installer_name","installer_email","installer_phone","note"
        ]).to_csv(BOOKINGS_CSV, index=False)

def is_lead_booked(lead_id: str) -> bool:
    _init_bookings_if_missing()
    df = pd.read_csv(BOOKINGS_CSV)
    return (df["lead_id"].astype(str) == str(lead_id)).any()

def append_booking(lead_row: dict, installer: dict, note: str="") -> None:
    _init_bookings_if_missing()
    row = {
        "booked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "lead_id": str(lead_row.get("lead_id","")).strip(),
        "regione": str(lead_row.get("regione","")).strip(),
        "installer_name": installer.get("name","").strip(),
        "installer_email": installer.get("email","").strip(),
        "installer_phone": installer.get("phone","").strip(),
        "note": note.strip(),
    }
    df = pd.read_csv(BOOKINGS_CSV)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(BOOKINGS_CSV, index=False)

def load_bookings() -> pd.DataFrame:
    _init_bookings_if_missing()
    return pd.read_csv(BOOKINGS_CSV)
