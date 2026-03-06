import streamlit as st
from .config import ADMIN_CODE, INSTALLER_CODE

def require_code(kind: str) -> bool:
    """Simple code-based access: kind in {'admin','installer'}."""
    key = f"authed_{kind}"
    if st.session_state.get(key):
        return True

    expected = ADMIN_CODE if kind == "admin" else INSTALLER_CODE
    if not expected:
        st.warning(f"Manca la secret {kind.upper()}_CODE. Impostala in Streamlit Secrets.")
        return False

    with st.form(f"login_{kind}", clear_on_submit=False):
        st.write("Inserisci il codice di accesso.")
        code = st.text_input("Codice", type="password")
        ok = st.form_submit_button("Entra")
    if ok:
        if code.strip() == expected:
            st.session_state[key] = True
            st.success("Accesso OK.")
            st.rerun()
        else:
            st.error("Codice errato.")
    return False
