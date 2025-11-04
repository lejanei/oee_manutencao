import streamlit as st
import pandas as pd
from db import get_engine, TABLES, fetch_df, count_rows, insert_row, update_row, delete_by_ids

st.title("🛠️ Máquinas")

engine = get_engine()
T = TABLES["maquinas"]

# Form
with st.expander("➕ Nova máquina", expanded=False):
    with st.form("form_maq"):
        nome = st.text_input("Nome", "")
        descricao = st.text_area("Descrição", "")
        ativo = st.number_input("Ativo (0/1)", min_value=0, max_value=1, step=1, value=1)
        ok = st.form_submit_button("Salvar", type="primary", use_container_width=True)
        if ok:
            if not nome:
                st.error("Informe o nome.")
            else:
                insert_row(engine, T, {"nome": nome, "descricao": descricao, "ativo": int(ativo)})
                st.success("Inserido!")
                st.rerun()



# Filtros
with st.expander("🔎 Filtros", expanded=False):
    f_nome = st.text_input("Nome contém", "")
    f_ativo = st.selectbox("Ativo", ["Todos","Somente ativos (1)","Somente inativos (0)"])
    page_size = st.number_input("Itens por página", 5, 200, 25, 5)

where, params = ["WHERE 1=1"], {}
if f_nome:
    where.append("AND nome LIKE :nome")
    params["nome"] = f"%{f_nome}%"
if f_ativo == "Somente ativos (1)":
    where.append("AND ativo = 1")
elif f_ativo == "Somente inativos (0)":
    where.append("AND ativo = 0")

where_sql = " " + " ".join(where)
order_sql = " ORDER BY nome ASC"
total = count_rows(engine, T, where_sql, params)
st.caption(f"Total com filtros: **{total}**")

# Listagem
page = st.number_input("Página", 1, max(1,(total-1)//page_size+1), 1)
offset = (page-1)*page_size
sql = f"SELECT id, nome, descricao, ativo FROM {T}{where_sql}{order_sql} LIMIT :lim OFFSET :off"
df = fetch_df(engine, sql, {**params, "lim": int(page_size), "off": int(offset)})

if df.empty:
    st.info("Nada encontrado.")
else:
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="grid_maq")
    changes = []
    for _, r in edited.iterrows():
        o = df.loc[df["id"]==r["id"]].iloc[0]
        if any(str(r[c])!=str(o[c]) for c in ["nome","descricao","ativo"]):
            changes.append({"id": int(r["id"]), "nome": str(r["nome"]), "descricao": str(r["descricao"]), "ativo": int(r["ativo"])})
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Salvar alterações", type="primary", use_container_width=True):
            for r in changes:
                update_row(engine, T, "id", r)
            st.success(f"{len(changes)} atualizado(s).")
            st.rerun()
    with c2:
        ids_del = st.multiselect("Selecionar IDs p/ excluir", edited["id"].tolist(), key="del_maq")
        if st.button("🗑️ Excluir selecionados", use_container_width=True):
            delete_by_ids(engine, T, ids_del)
            st.success(f"{len(ids_del)} excluído(s).")
            st.rerun()

    st.download_button("⬇️ Exportar CSV", edited.to_csv(index=False).encode("utf-8"), "maquinas.csv", "text/csv", use_container_width=True)
