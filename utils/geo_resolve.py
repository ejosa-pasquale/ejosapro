from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COMUNI_CAP_CSV = DATA_DIR / "gi_comuni_cap.csv"


def _norm(s: str) -> str:
    s = str(s or "")
    s = s.casefold()
    s = re.sub(r"[^a-zà-ÿ0-9\s'\-]", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _fix_mojibake(s: str) -> str:
    """Try to fix common UTF-8->latin1 mojibake (e.g. 'AgliÃ¨' -> 'Agliè')."""
    s = str(s or "")
    if "Ã" not in s and "Â" not in s:
        return s
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        return s


@st.cache_data(show_spinner=False)
def load_comuni_cap() -> pd.DataFrame:
    """Load Italian comuni dataset (CAP / province / region)."""
    if not COMUNI_CAP_CSV.exists():
        # App can still run without geo dataset; resolver will be best-effort.
        return pd.DataFrame(columns=[
            "denominazione_ita", "cap", "sigla_provincia", "denominazione_regione"
        ])

    # This dataset is typically semicolon-separated, latin1 encoded.
    df = pd.read_csv(COMUNI_CAP_CSV, sep=";", encoding="latin1", dtype=str)
    # Keep only what we need.
    keep = [
        "denominazione_ita",
        "cap",
        "sigla_provincia",
        "denominazione_regione",
    ]
    for c in keep:
        if c not in df.columns:
            df[c] = ""
    df = df[keep].copy()

    df["cap"] = df["cap"].astype(str).str.strip()
    df["sigla_provincia"] = df["sigla_provincia"].astype(str).str.strip().str.upper()
    df["denominazione_ita"] = df["denominazione_ita"].astype(str).str.strip()
    df["denominazione_regione"] = df["denominazione_regione"].astype(str).str.strip()

    # Fix common encoding issues (dataset often contains mixed/invalid bytes)
    df["denominazione_ita"] = df["denominazione_ita"].map(_fix_mojibake)
    df["denominazione_regione"] = df["denominazione_regione"].map(_fix_mojibake)
    df["_comune_key"] = df["denominazione_ita"].map(_norm)
    return df


@dataclass
class GeoGuess:
    citta: str = ""
    regione: str = ""
    provincia_sigla: str = ""
    note: str = ""


_RE_CAP = re.compile(r"\b(\d{5})\b")
_RE_PROV = re.compile(r"\(([A-Z]{2})\)")


def infer_city_region_from_address(address: str) -> GeoGuess:
    """Best-effort resolver for city/region from a free-form Italian address."""
    addr_raw = str(address or "").strip()
    if not addr_raw:
        return GeoGuess(note="indirizzo vuoto")

    addr = re.sub(r"\s+", " ", addr_raw.replace("\n", " ")).strip()
    cap = _RE_CAP.search(addr)
    cap = cap.group(1) if cap else ""
    prov = _RE_PROV.search(addr)
    prov = prov.group(1) if prov else ""

    comuni = load_comuni_cap()
    if comuni.empty:
        return GeoGuess(note="dataset comuni mancante")

    # 1) Strong match: CAP + (PR)
    if cap and prov:
        sub = comuni[(comuni["cap"] == cap) & (comuni["sigla_provincia"] == prov)]
        if len(sub) == 1:
            r = sub.iloc[0]
            return GeoGuess(citta=r["denominazione_ita"], regione=r["denominazione_regione"], provincia_sigla=prov)
        if len(sub) > 1:
            # Rare, but keep deterministic
            r = sub.sort_values("denominazione_ita").iloc[0]
            return GeoGuess(
                citta=r["denominazione_ita"],
                regione=r["denominazione_regione"],
                provincia_sigla=prov,
                note=f"cap+prov match multiplo ({len(sub)})",
            )

    # 2) Parse pattern: 12345 Città (PR)
    m = re.search(r"\b(\d{5})\s+(.+?)\s*\(([A-Z]{2})\)", addr)
    if m:
        cap2, city2, prov2 = m.group(1), m.group(2), m.group(3)
        sub = comuni[(comuni["cap"] == cap2) & (comuni["sigla_provincia"] == prov2)]
        if len(sub) >= 1:
            r = sub.sort_values("denominazione_ita").iloc[0]
            note = "" if len(sub) == 1 else f"cap+prov match multiplo ({len(sub)})"
            return GeoGuess(citta=r["denominazione_ita"], regione=r["denominazione_regione"], provincia_sigla=prov2, note=note)

        # Fallback on city name itself
        gg = infer_from_city_only(city2, prefer_prov=prov2)
        gg.note = (gg.note + "; " if gg.note else "") + "da pattern cap+citta+prov (cap non trovato nel dataset)"
        return gg

    # 3) CAP only
    if cap:
        sub = comuni[comuni["cap"] == cap]
        if len(sub) == 1:
            r = sub.iloc[0]
            return GeoGuess(citta=r["denominazione_ita"], regione=r["denominazione_regione"], provincia_sigla=r["sigla_provincia"], note="da CAP")
        if len(sub) > 1:
            # Many CAP map to multiple comuni. Pick first alphabetical but warn.
            r = sub.sort_values("denominazione_ita").iloc[0]
            return GeoGuess(
                citta=r["denominazione_ita"],
                regione=r["denominazione_regione"],
                provincia_sigla=r["sigla_provincia"],
                note=f"cap condiviso ({len(sub)} comuni) — scelta automatica",
            )

    # 4) Province only: not enough to determine city
    if prov:
        # Find any comune in that province just to infer region, leave city blank.
        sub = comuni[comuni["sigla_provincia"] == prov]
        if len(sub) > 0:
            reg = sub.iloc[0]["denominazione_regione"]
            return GeoGuess(citta="", regione=reg, provincia_sigla=prov, note="solo provincia — città non determinabile")

    # 5) Try to match a comune name inside the address text
    return infer_from_text_contains_comune(addr)


def infer_from_city_only(city: str, *, prefer_prov: str = "", prefer_cap: str = "") -> GeoGuess:
    city_norm = _norm(city)
    if not city_norm:
        return GeoGuess(note="città vuota")

    comuni = load_comuni_cap()
    sub = comuni[comuni["_comune_key"] == city_norm]
    if prefer_prov:
        sub2 = sub[sub["sigla_provincia"] == prefer_prov]
        if len(sub2) >= 1:
            r = sub2.iloc[0]
            return GeoGuess(citta=r["denominazione_ita"], regione=r["denominazione_regione"], provincia_sigla=r["sigla_provincia"], note="da comune+prov")
    if prefer_cap:
        sub2 = sub[sub["cap"] == prefer_cap]
        if len(sub2) >= 1:
            r = sub2.iloc[0]
            return GeoGuess(citta=r["denominazione_ita"], regione=r["denominazione_regione"], provincia_sigla=r["sigla_provincia"], note="da comune+cap")

    if len(sub) == 1:
        r = sub.iloc[0]
        return GeoGuess(citta=r["denominazione_ita"], regione=r["denominazione_regione"], provincia_sigla=r["sigla_provincia"], note="da comune")
    if len(sub) > 1:
        r = sub.sort_values(["denominazione_regione", "sigla_provincia", "cap"]).iloc[0]
        return GeoGuess(
            citta=r["denominazione_ita"],
            regione=r["denominazione_regione"],
            provincia_sigla=r["sigla_provincia"],
            note=f"nome comune ambiguo ({len(sub)} match) — scelta automatica",
        )
    return GeoGuess(note="comune non trovato")


@st.cache_data(show_spinner=False)
def _comune_key_to_rows() -> Dict[str, List[Tuple[str, str, str, str]]]:
    """Index for faster matching: comune_key -> list of (comune, regione, prov, cap)."""
    comuni = load_comuni_cap()
    out: Dict[str, List[Tuple[str, str, str, str]]] = {}
    for r in comuni.itertuples(index=False):
        key = getattr(r, "_comune_key")
        out.setdefault(key, []).append(
            (getattr(r, "denominazione_ita"), getattr(r, "denominazione_regione"), getattr(r, "sigla_provincia"), getattr(r, "cap"))
        )
    return out


@st.cache_data(show_spinner=False)
def _sorted_comune_keys_by_len() -> List[str]:
    idx = _comune_key_to_rows()
    keys = list(idx.keys())
    keys.sort(key=len, reverse=True)
    return keys


def infer_from_text_contains_comune(text: str) -> GeoGuess:
    txt = _norm(text)
    if not txt:
        return GeoGuess(note="testo vuoto")

    idx = _comune_key_to_rows()
    for key in _sorted_comune_keys_by_len():
        # word-boundary-ish match to reduce false positives
        if re.search(rf"\b{re.escape(key)}\b", txt):
            rows = idx.get(key, [])
            if len(rows) == 1:
                comune, regione, prov, cap = rows[0]
                return GeoGuess(citta=comune, regione=regione, provincia_sigla=prov, note="da match comune in indirizzo")
            if len(rows) > 1:
                comune, regione, prov, cap = sorted(rows, key=lambda x: (x[1], x[2], x[3], x[0]))[0]
                return GeoGuess(
                    citta=comune,
                    regione=regione,
                    provincia_sigla=prov,
                    note=f"match comune ambiguo ({len(rows)}) — scelta automatica",
                )
    return GeoGuess(note="nessun comune individuato")
