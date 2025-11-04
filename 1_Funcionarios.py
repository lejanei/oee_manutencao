import streamlit as st
import pandas as pd
from db import get_engine, TABLES, fetch_df, count_rows, insert_row, update_row, delete_by_ids

st.title("👥 Funcionários")

engine = get_engine()
T = TABLES["funcionarios"]

# --------- Formulário ---------
with st.expander("➕ Novo funcionário", expanded=False):
    with st.form("form_func"):
        nome = st.text_input("Nome", "")
        cargo = st.text_input("Cargo", "")
        ok = st.form_submit_button("Salvar", type="primary", use_container_width=True)
        if ok:
            if not nome or not cargo:
                st.error("Preencha nome e cargo.")
            else:
                insert_row(engine, T, {"nome": nome, "cargo": cargo})
                st.success("Inserido!")
                st.rerun()

# --------- Paginação (sem filtros) ---------
#page_size = st.number_input("Itens por página", min_value=5, max_value=200, value=25, step=5, key="func_page_size")
page_size = 50

where_sql = " WHERE 1=1"
params = {}
order_sql = " ORDER BY nome ASC"
total = count_rows(engine, T, where_sql, params)
st.caption(f"Total: **{total}**")

#page = st.number_input(
#   "Página",
#    min_value=1,
#    max_value=max(1, (total - 1) // int(page_size) + 1),
#    value=1,
#    step=1,
#    key="func_page",
#)
#offset = (int(page) - 1) * int(page_size)
offset = 0
# --------- Listagem ---------
sql = f"SELECT id, nome, cargo FROM {T}{where_sql}{order_sql} LIMIT :lim OFFSET :off"
df = fetch_df(engine, sql, {**params, "lim": int(page_size), "off": int(offset)})

if df.empty:
    st.info("Nada encontrado.")
else:
    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="grid_func",
    )

    # detectar alterações (comparando com df original)
    changes = []
    for _, r in edited.iterrows():
        o = df.loc[df["id"] == r["id"]].iloc[0]
        if any(str(r[c]) != str(o[c]) for c in ["nome", "cargo"]):
            changes.append({"id": int(r["id"]), "nome": str(r["nome"]), "cargo": str(r["cargo"])})

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Salvar alterações", type="primary", use_container_width=True, key="func_btn_save"):
            for r in changes:
                update_row(engine, T, "id", r)
            st.success(f"{len(changes)} atualizado(s).")
            st.rerun()

    with c2:
        ids_del = st.multiselect("Selecionar IDs p/ excluir", edited["id"].tolist(), key="func_del_ids")
        if st.button("🗑️ Excluir selecionados", use_container_width=True, key="func_btn_del"):
            if ids_del:
                delete_by_ids(engine, T, ids_del)
                st.success(f"{len(ids_del)} excluído(s).")
                st.rerun()
            else:
                st.warning("Nenhum ID selecionado.")

    st.download_button(
        "⬇️ Exportar CSV",
        edited.to_csv(index=False).encode("utf-8"),
        "funcionarios.csv",
        "text/csv",
        use_container_width=True,
        key="func_btn_csv",
    )
