# nav.py
import streamlit as st
from auth import get_authenticator, render_userbox, can

def render_sidebar():
    """Desenha o sidebar (userbox + navegação) em qualquer página, SEM criar novo autenticador."""
    authenticator = get_authenticator()  # é singleton por cache_resource
    render_userbox(authenticator)

    with st.sidebar:
        st.markdown("## Navegação")
        st.page_link("App.py", label="🏠 Início")

        if can("access_funcionarios"):
            st.page_link("pages/1_Funcionarios.py", label="👥 Funcionários")
        if can("access_maquinas"):
            st.page_link("pages/2_Maquinas.py", label="🏭 Máquinas")

        st.page_link("pages/3_Ordens_de_Servico.py", label="🧾 OS (Corretiva)")
        st.page_link("pages/4_Ordens_de_Preventiva.py", label="🧾 Preventiva")
        st.page_link("pages/5_OEE.py", label="📊 OEE")
