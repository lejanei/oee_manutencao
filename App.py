# App.py
import streamlit as st
from sqlalchemy import text
from db import get_engine
from auth import get_authenticator, inject_role_from_authenticator, can
from nav import render_sidebar

# --------------------------------
# Configuração da página
# --------------------------------
st.set_page_config(
    page_title="Cori • Manutenção & OEE",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------
# Autenticação (login) — UMA vez
# --------------------------------
authenticator = get_authenticator()
# use uma key fixa para este arquivo (evita duplicate form)
inject_role_from_authenticator(authenticator, key="login_main")

# --------------------------------
# Sidebar customizado persistente
# --------------------------------
render_sidebar()  # desenha userbox + navegação (sem login aqui)

# --------------------------------
# Conteúdo principal
# --------------------------------
st.title("Cori • Manutenção & OEE")
st.caption("Autenticação + Regras por papel (operador, manutentor, admin)")

st.subheader("Status de conexão")
try:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.success("✅ Conectado ao MySQL.")
except Exception as e:
    st.error(f"❌ Erro de conexão: {e}")

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
