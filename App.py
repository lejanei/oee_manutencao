# App.py
import streamlit as st
from sqlalchemy import text
from db import get_engine
from auth import get_authenticator, inject_role_from_authenticator, render_userbox, can

# -----------------------------
# Configuração da página
# -----------------------------
from nav import render_sidebar

st.set_page_config(
    page_title="Cori • Manutenção & OEE",
    layout="wide",
    initial_sidebar_state="expanded",  # 🔒 mantém o sidebar aberto
)

render_sidebar()  # ← garante o sidebar persistente nesta página

# -----------------------------
# Título
# -----------------------------
st.title("Cori • Manutenção & OEE")
st.caption("Autenticação + Regras por papel (operador, manutentor, admin)")

# -----------------------------
# Autenticação
# -----------------------------
authenticator = get_authenticator()

# Evita relogar duas vezes no mesmo ciclo
if "auth_inited" not in st.session_state:
    inject_role_from_authenticator(authenticator)
    st.session_state["auth_inited"] = True

inject_role_from_authenticator(authenticator)
# -----------------------------
# Navegação (condicionada por papel)
# -----------------------------


# -----------------------------
# Saúde da conexão MySQL
# -----------------------------
st.subheader("Status de conexão")
try:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.success("✅ Conectado ao MySQL.")
except Exception as e:
    st.error(f"❌ Erro de conexão: {e}")

# -----------------------------
# Informações sobre permissões
# -----------------------------
st.divider()
st.markdown(
    """
**Regras de acesso:**

- **operador**: cria OS; vê listagens; **sem** editar/excluir; **sem** acesso a **Funcionários**/**Máquinas**  
- **manutentor**: cria **e** edita OS e Preventivas; **sem** excluir; **sem** acesso a **Funcionários**/**Máquinas**  
- **admin**: acesso **total**
"""
)

st.info(
    "As permissões de criar/editar/excluir são aplicadas **dentro** das páginas. "
    "Se um botão/ação não aparece para você, seu papel não permite essa operação."
)
