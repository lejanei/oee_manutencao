# auth.py
import streamlit as st
import streamlit_authenticator as stauth
from typing import List, Tuple, Dict, Any

# ============================================================
# UTILITÁRIO: copiar st.secrets (read-only) para dict normal
# ============================================================
def _secrets_to_dict(obj):
    """Converte objetos de st.secrets em dicionários comuns (deep copy)."""
    try:
        items = dict(obj)
    except Exception:
        return obj
    out = {}
    for k, v in items.items():
        out[k] = _secrets_to_dict(v) if hasattr(v, "keys") else v
    return out

# ============================================================
# AUTHENTICATOR — instância única por sessão (sem cache de widget)
# ============================================================
def get_authenticator():
    """Cria o autenticador uma única vez por sessão, sem usar cache."""
    if "_authenticator" in st.session_state:
        return st.session_state["_authenticator"]

    cfg = _secrets_to_dict(st.secrets["auth"])
    credentials = _secrets_to_dict(cfg.get("credentials", {}))
    cookie_name = cfg.get("cookie_name", "app-auth")
    signature_key = cfg.get("signature_key", "change-me")
    cookie_expiry_days = cfg.get("cookie_expiry_days", 7)

    auth = stauth.Authenticate(credentials, cookie_name, signature_key, cookie_expiry_days)
    st.session_state["_authenticator"] = auth
    return auth

# ============================================================
# NORMALIZA retorno do login para (name, auth_status, username)
# ============================================================
def _normalize_login_return(ret: Any) -> Tuple[str|None, bool|None, str|None]:
    # tuple clássico
    if isinstance(ret, tuple) and len(ret) == 3:
        return ret[0], ret[1], ret[2]
    # dict moderno
    if isinstance(ret, dict):
        return (
            ret.get("name"),
            ret.get("authentication_status"),
            ret.get("username"),
        )
    # bool (raro): apenas status
    if isinstance(ret, bool):
        return (
            st.session_state.get("name"),
            ret,
            st.session_state.get("username"),
        )
    # None: tenta session_state
    return (
        st.session_state.get("name"),
        st.session_state.get("authentication_status"),
        st.session_state.get("username"),
    )

# ============================================================
# LOGIN / LOGOUT / INFO DO USUÁRIO
# ============================================================
def inject_role_from_authenticator(authenticator, key: str = "login_main"):
    """
    Renderiza o login no sidebar UMA vez na página principal.
    Use uma key exclusiva para evitar 'duplicate form key'.
    """
    try:
        ret = authenticator.login(location="sidebar", key=key, clear_on_submit=True)
    except TypeError:
        # fallback p/ versões antigas sem esses kwargs
        ret = authenticator.login(location="sidebar")

    name, auth_status, username = _normalize_login_return(ret)

    if auth_status:
        st.session_state["authentication_status"] = True
        if username: st.session_state["username"] = username
        if name:     st.session_state["name"] = name
        # papel a partir do secrets
        if username:
            role = st.secrets["auth"]["credentials"]["usernames"][username].get("role", "operador")
        else:
            role = st.session_state.get("role", "operador")
        st.session_state["role"] = role

    elif auth_status is False:
        st.session_state["authentication_status"] = False
        st.error("Usuário/senha inválidos.")
    else:
        st.info("Informe suas credenciais.")

def render_userbox(authenticator):
    """Mostra informações do usuário logado e botão de logout (sidebar)."""
    if st.session_state.get("authentication_status") is True:
        with st.sidebar:
            st.write(f"👤 **{st.session_state.get('name', '')}**")
            st.write(f"🔑 Papel: **{st.session_state.get('role', 'anon')}**")
            # key única baseada no username evita duplicação entre páginas
            logout_key = f"logout_btn_{st.session_state.get('username','anon')}"
            try:
                authenticator.logout(location="sidebar", key=logout_key)
            except TypeError:
                authenticator.logout("Sair", "sidebar")

# ============================================================
# PERMISSÕES POR PAPEL
# ============================================================
def current_username(): return st.session_state.get("username")
def current_name(): return st.session_state.get("name")
def current_role(): return st.session_state.get("role", "anon")
def is_logged(): return st.session_state.get("authentication_status", None) is True

ROLE_PERMS = {
    "operador": {
        "access_funcionarios": False,
        "access_maquinas": False,
        "view_os": True, "create_os": True, "edit_os": False, "delete_os": False,
        "view_prev": True, "create_prev": False, "edit_prev": False, "delete_prev": False,
        "view_oee": True,
    },
    "manutentor": {
        "access_funcionarios": False,
        "access_maquinas": False,
        "view_os": True, "create_os": True, "edit_os": True, "delete_os": False,
        "view_prev": True, "create_prev": True, "edit_prev": True, "delete_prev": False,
        "view_oee": True,
    },
    "admin": {
        "access_funcionarios": True,
        "access_maquinas": True,
        "view_os": True, "create_os": True, "edit_os": True, "delete_os": True,
        "view_prev": True, "create_prev": True, "edit_prev": True, "delete_prev": True,
        "view_oee": True,
    },
}

def can(action: str) -> bool:
    """Verifica se o papel atual tem permissão para a ação."""
    return ROLE_PERMS.get(current_role(), {}).get(action, False)

def gate_page(allowed_roles: List[str]):
    """Bloqueia o acesso à página caso o papel não esteja autorizado."""
    if not is_logged():
        st.error("Você precisa estar autenticado.")
        st.stop()
    if current_role() not in allowed_roles:
        st.error("Acesso negado para seu perfil.")
        st.stop()
