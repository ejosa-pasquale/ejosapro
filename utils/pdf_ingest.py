from __future__ import annotations

import datetime as dt
import re
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from .geo_resolve import infer_city_region_from_address


_RE_EMAIL = re.compile(r"[\w.+'-]+@[\w.-]+\.[A-Za-z]{2,}")


def _clean(s: str) -> str:
    s = str(s or "")
    s = re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip()
    return s


def _remove_emails(s: str) -> str:
    return _RE_EMAIL.sub("", s or "").replace("  ", " ").strip()


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts: List[str] = []
    for page in doc:
        parts.append(page.get_text("text"))
    return "\n".join(parts)


def _find_field_value(text: str, field: str) -> str:
    """Find a 'Campo Valore' style field. Best-effort."""
    # PDFs we saw are like:
    # Campo\nValore\nIndirizzo:\n<value>\nTipo abitazione:\n<value>...
    lines = [l.rstrip() for l in text.splitlines()]
    field_cf = field.casefold()
    for i, ln in enumerate(lines):
        if ln.strip().casefold().startswith(field_cf):
            # value might be on same line after ':'
            after = ln.split(":", 1)[1] if ":" in ln else ""
            after = after.strip()
            if after:
                return after
            # else take next non-empty line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                return lines[j].strip()
    return ""


def _parse_budget_eur(text: str) -> Optional[int]:
    # "Il costo della tua Wallbox è tra: €1396 e €1622"
    m = re.search(
        r"costo\s+della\s+tua\s+wallbox\s+\S*\s*tra\s*:?\s*€?\s*([0-9.]+)\s*e\s*€?\s*([0-9.]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    a = int(m.group(1).replace(".", ""))
    b = int(m.group(2).replace(".", ""))
    return int(round((a + b) / 2))


def _parse_preventivo_id(text: str, fallback_filename: str) -> str:
    # e.g. "Numero Preventivo: #260210-201847"
    m = re.search(r"Numero\s+Preventivo\s*:\s*#([0-9]{6,})-([0-9]{3,})", text, flags=re.IGNORECASE)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"#([0-9]{6,})-([0-9]{3,})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    # fallback to filename stem (safe)
    stem = re.sub(r"\.[Pp][Dd][Ff]$", "", fallback_filename or "")
    stem = stem.strip() or "lead"
    return stem[:60]


def _parse_data_inserimento_from_lead_id(lead_id: str) -> str:
    # If lead_id starts with YYMMDD...
    m = re.match(r"^(\d{6})", str(lead_id))
    if not m:
        return ""
    yymmdd = m.group(1)
    yy = int(yymmdd[0:2])
    mm = int(yymmdd[2:4])
    dd = int(yymmdd[4:6])
    year = 2000 + yy
    try:
        d = dt.date(year, mm, dd)
        return d.isoformat()
    except Exception:
        return ""


def parse_pdf_to_lead(pdf_bytes: bytes, filename: str = "") -> Dict[str, str]:
    text = extract_text_from_pdf_bytes(pdf_bytes)
    text_clean = text.replace("\r", "")

    indirizzo = _find_field_value(text_clean, "Indirizzo")
    tipologia = _find_field_value(text_clean, "Voglio caricare")
    if not tipologia:
        # fallback from another field we saw
        inc = _find_field_value(text_clean, "Il servizio include installazione")
        tipologia = inc or ""

    budget = _parse_budget_eur(text_clean)
    lead_id = _parse_preventivo_id(text_clean, filename)
    data_ins = _parse_data_inserimento_from_lead_id(lead_id)

    # contact email: prefer from filename, else from pdf content
    email = ""
    if filename:
        m = _RE_EMAIL.search(filename)
        if m:
            email = m.group(0)
    if not email:
        m = _RE_EMAIL.search(text_clean)
        if m:
            email = m.group(0)

    geo = infer_city_region_from_address(indirizzo)

    note_parts = []
    if tipologia:
        note_parts.append(f"Tipologia: {tipologia}")
    if indirizzo:
        # keep address but strip emails
        note_parts.append(f"Indirizzo: {_remove_emails(indirizzo)}")
    if geo.citta or geo.regione:
        note_parts.append(f"Località: {geo.citta} ({geo.regione})".strip())
    if geo.note:
        note_parts.append(f"Geo: {geo.note}")
    if filename:
        note_parts.append(f"Fonte file: {re.sub(_RE_EMAIL, '', filename).strip()}")
    note = " | ".join([p for p in note_parts if p]).strip(" |")

    # Remove emails from note entirely
    note = _remove_emails(note)

    out: Dict[str, str] = {
        "lead_id": str(lead_id),
        "data_inserimento": data_ins,
        "regione": geo.regione,
        "citta": geo.citta,
        "indirizzo": indirizzo,
        "metri_mq": "",  # not provided by these PDFs
        "tipologia": tipologia,
        "budget_eur": "" if budget is None else str(budget),
        "note": note,
        "contatto_email": email,
        "contatto_telefono": "",
    }
    return out


def parse_many_pdfs(files: List[Tuple[str, bytes]]) -> List[Dict[str, str]]:
    """files is list of (filename, bytes)."""
    rows: List[Dict[str, str]] = []
    for filename, b in files:
        try:
            rows.append(parse_pdf_to_lead(b, filename=filename))
        except Exception as e:
            rows.append({
                "lead_id": re.sub(r"\.[Pp][Dd][Ff]$", "", filename or "lead"),
                "data_inserimento": "",
                "regione": "",
                "citta": "",
                "indirizzo": "",
                "metri_mq": "",
                "tipologia": "",
                "budget_eur": "",
                "note": f"ERRORE parsing PDF: {e}",
                "contatto_email": "",
                "contatto_telefono": "",
            })
    return rows
