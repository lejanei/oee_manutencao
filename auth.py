import streamlit as st
import streamlit_authenticator as stauth
from typing import List

def get_authenticator():
    cfg = st.secrets["auth"]
    credentials = cfg["credentials"]
    cookie_name = cfg.get("cookie_name", "app-auth")
    signature_key = cfg.get("signature_key", "change-me")
    cookie_expiry_days = cfg.get("cookie_expiry_days", 7)
    return stauth.Authenticate(credentials, cookie_name, signature_key, cookie_expiry_days)

def is_logged(): return st.session_state.get("authentication_status", None) is True
def current_username(): return st.session_state.get("username")
def current_name(): return st.session_state.get("name")
def current_role(): return st.session_state.get("role", "anon")

ROLE_PERMS = {
    "operador": {
        "access_funcionarios": False, "access_maquinas": False,
        "view_os": True, "create_os": True, "edit_os": False, "delete_os": False,
        "view_prev": True, "create_prev": False, "edit_prev": False, "delete_prev": False,
        "view_oee": True, "create_oee": False, "edit_oee": False,
    },
    "manutentor": {
        "access_funcionarios": False, "access_maquinas": False,
        "view_os": True, "create_os": True, "edit_os": True, "delete_os": False,
        "view_prev": True, "create_prev": True, "edit_prev": True, "delete_prev": False,
        "view_oee": True, "create_oee": False, "edit_oee": False,
    },
    "admin": {
        "access_funcionarios": True, "access_maquinas": True,
        "view_os": True, "create_os": True, "edit_os": True, "delete_os": True,
        "view_prev": True, "create_prev": True, "edit_prev": True, "delete_prev": True,
        "view_oee": True, "create_oee": True, "edit_oee": True,
    },
}

def can(action: str) -> bool:
    return ROLE_PERMS.get(current_role(), {}).get(action, False)

def gate_page(allowed_roles: List[str]):
    if not is_logged():
        st.error("Você precisa estar autenticado.")
        st.stop()
    if current_role() not in allowed_roles:
        st.error("Acesso negado para seu perfil.")
        st.stop()

def inject_role_from_authenticator(authenticator):
    name, auth_status, username = authenticator.login("Login", "sidebar")
    if auth_status:
        st.session_state["authentication_status"] = True
        st.session_state["username"] = username
        st.session_state["name"] = name
        role = st.secrets["auth"]["credentials"]["usernames"][username].get("role", "operador")
        st.session_state["role"] = role
    elif auth_status is False:
        st.session_state["authentication_status"] = False
        st.error("Usuário/senha inválidos.")
    else:
        st.info("Informe suas credenciais.")

def render_userbox(authenticator):
    if is_logged():
        with st.sidebar:
            st.write(f"👤 **{current_name()}**")
            st.write(f"🔑 Papel: **{current_role()}**")
            authenticator.logout("Sair", "sidebar")
