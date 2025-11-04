import streamlit as st
from db import get_engine

st.set_page_config(
    page_title="Cori • Manutenção & OEE",
    page_icon="🛠️",
    layout="wide",
)

st.title("Cori • Manutenção & OEE")




st.subheader("Status de conexão")
try:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute("SELECT 1")
    st.success("✅ Conectado ao MySQL.")
except Exception as e:
    st.error(f"❌ Erro de conexão: {e}")

st.divider()
st.markdown("""
### Dicas
- Ajuste os *Secrets* do app (MySQL) no Streamlit Cloud.
- Use as páginas no menu lateral para CRUD e lançamentos.
""")
