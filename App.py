import streamlit as st
from sqlalchemy import text
from db import get_engine
from auth import get_authenticator, inject_role_from_authenticator, render_userbox, can

st.set_page_config(page_title="Cori • Manutenção & OEE", page_icon="🛠️", layout="wide")
st.title("Cori • Manutenção & OEE")
st.caption("Autenticação + Regras por papel")

# Autenticação
authenticator = get_authenticator()
inject_role_from_authenticator(authenticator)
render_userbox(authenticator)

# Menu condicionado por papel
with st.sidebar:
    st.markdown("## Navegação")
    st.page_link("app.py", label="🏠 Início", icon="🏠")
    if can("access_funcionarios"):
        st.page_link("pages/1_Funcionarios.py", label="👥 Funcionários", icon="👥")
    if can("access_maquinas"):
        st.page_link("pages/2_Maquinas.py", label="🏭 Máquinas", icon="🏭")
    st.page_link("pages/3_Ordens_de_Servico.py", label="🧾 OS (Corretiva)", icon="🧾")
    st.page_link("pages/4_Ordens_de_Preventiva.py", label="🧾 Preventiva", icon="🧾")
    st.page_link("pages/5_OEE.py", label="📊 OEE", icon="📊")

st.subheader("Status de conexão")
try:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.success("✅ Conectado ao MySQL.")
except Exception as e:
    st.error(f"❌ Erro de conexão: {e}")

st.divider()
st.markdown("""
**Regras:**  
- operador: cria OS; vê listagens; sem editar/excluir; sem Funcionários/Máquinas  
- manutentor: cria/edita OS e Preventivas; sem excluir; sem Funcionários/Máquinas  
- admin: total
""")
