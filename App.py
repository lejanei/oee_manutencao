import streamlit as st
from sqlalchemy import text
from db import get_engine

st.set_page_config(
    page_title="Cori • Manutenção & OEE",
    page_icon="🛠️",
    layout="wide",
)

st.title("Cori • Manutenção & OEE")
st.caption("Streamlit • HostGator MySQL • GitHub Deploy")


st.subheader("Status de conexão")
try:
    engine = get_engine()
    with engine.connect() as conn:
        # SQLAlchemy 2.x: use text(...) ou exec_driver_sql(...)
        conn.execute(text("SELECT 1"))
    st.success("✅ Conectado ao MySQL.")
except Exception as e:
    st.error(f"❌ Erro de conexão: {e}")

st.divider()
st.markdown("""
### Dicas
- Configure os **Secrets** (MySQL) no Streamlit Cloud (Settings → Secrets).
- Use as páginas no menu lateral para CRUD e lançamentos.
""")
