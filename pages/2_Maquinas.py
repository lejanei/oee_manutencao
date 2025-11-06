import streamlit as st
import pandas as pd
from auth import gate_page
from db import get_engine, TABLES, fetch_df, count_rows, insert_row, update_row, delete_by_ids

from nav import render_sidebar

st.set_page_config(
    page_title="Cori • Manutenção & OEE",
    layout="wide",
    initial_sidebar_state="expanded",  # 🔒 mantém o sidebar aberto
)

render_sidebar()  # ← garante o sidebar persistente nesta página


gate_page(["admin"])
st.title("🏭 Máquinas")
engine = get_engine()
T = TABLES["maquinas"]

with st.expander("➕ Nova máquina", expanded=False):
    with st.form("form_maq"):
        nome = st.text_input("Nome", "")
        descricao = st.text_area("Descrição", "")
        ativo = st.number_input("Ativo (0/1)", min_value=0, max_value=1, value=1, step=1)
        ok = st.form_submit_button("Salvar", type="primary", use_container_width=True)
        if ok:
            if not nome: st.error("Informe o nome.")
            else:
                insert_row(engine, T, {"nome": nome, "descricao": descricao, "ativo": int(ativo)})
                st.success("Inserido!"); st.rerun()



page_size = st.number_input("Itens por página", 5, 200, 25, 5, key="maq_page_size")
total = count_rows(engine, T, " WHERE 1=1", {})
st.caption(f"Total: **{total}**")
page = st.number_input("Página", 1, max(1, (total-1)//int(page_size)+1), 1, key="maq_page")
offset = (int(page)-1)*int(page_size)

df = fetch_df(engine, f"SELECT id, nome, descricao, ativo FROM {T} ORDER BY nome ASC LIMIT :lim OFFSET :off",
              {"lim": int(page_size), "off": int(offset)})

if df.empty:
    st.info("Nada encontrado.")
else:
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="grid_maqs")
    changes = []
    for _, r in edited.iterrows():
        o = df.loc[df["id"] == r["id"]].iloc[0]
        if any(str(r[c]) != str(o[c]) for c in ["nome","descricao","ativo"]):
            changes.append({"id": int(r["id"]), "nome": str(r["nome"]), "descricao": str(r["descricao"]), "ativo": int(r["ativo"])})
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Salvar alterações", type="primary", use_container_width=True, key="maq_btn_save"):
            for r in changes: update_row(engine, T, "id", r)
            st.success(f"{len(changes)} atualizado(s)."); st.rerun()
    with c2:
        ids_del = st.multiselect("Selecionar IDs p/ excluir", edited["id"].tolist(), key="maq_del_ids")
        if st.button("🗑️ Excluir selecionados", use_container_width=True, key="maq_btn_del"):
            if ids_del: delete_by_ids(engine, T, ids_del); st.success(f"{len(ids_del)} excluído(s)."); st.rerun()
            else: st.warning("Nenhum ID selecionado.")
