import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
from db import (
    get_engine, TABLES, fetch_df, count_rows, insert_row, update_row, delete_by_ids,
    options_maquinas, options_funcionarios
)

# ----------------- Helpers -----------------
def _as_date(v):
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return datetime.now().date()

def _as_time(v):
    try:
        t = pd.to_datetime(v).time()
        return t.replace(microsecond=0)
    except Exception:
        return datetime.now().time().replace(second=0, microsecond=0)

def _load_os_record(engine, os_id: int):
    sql = """
        SELECT id, id_maquina, id_funcionario, tipo_de_servico, local_do_problema,
               descricao_do_problema, datahora_inicio, datahora_fim, concluido, observacao
        FROM ordens_servico
        WHERE id=:id
    """
    df = fetch_df(engine, sql, {"id": int(os_id)})
    return None if df.empty else df.iloc[0].to_dict()

def _inject_edit_state(rec, id2maqname, id2funcname):
    """Armazena valores carregados do BD em chaves internas _prefill_* (não usadas por widgets)."""
    st.session_state["_prefill_os_maquina_name"] = id2maqname.get(int(rec["id_maquina"]), "") if rec.get("id_maquina") else ""
    st.session_state["_prefill_os_resp_name"]    = id2funcname.get(int(rec["id_funcionario"]), "—") if rec.get("id_funcionario") else "—"
    st.session_state["_prefill_os_tipo"]      = str(rec.get("tipo_de_servico") or "")
    st.session_state["_prefill_os_local"]     = str(rec.get("local_do_problema") or "")
    st.session_state["_prefill_os_desc"]      = str(rec.get("descricao_do_problema") or "")
    st.session_state["_prefill_os_concluido"] = int(rec.get("concluido") or 0)
    st.session_state["_prefill_os_obs"]       = str(rec.get("observacao") or "")
    st.session_state["_prefill_os_dti"] = _as_date(rec.get("datahora_inicio"))
    st.session_state["_prefill_os_ti"]  = _as_time(rec.get("datahora_inicio"))
    st.session_state["_prefill_os_dtf"] = _as_date(rec.get("datahora_fim"))
    st.session_state["_prefill_os_tf"]  = _as_time(rec.get("datahora_fim"))

def _apply_os_prefill_to_widgets():
    """Copia _prefill_* para as keys dos widgets antes de renderizá-los."""
    ss = st.session_state
    map_simple = {
        "os_ed_maquina_name": "_prefill_os_maquina_name",
        "os_ed_resp_name": "_prefill_os_resp_name",
        "os_ed_tipo": "_prefill_os_tipo",
        "os_ed_local": "_prefill_os_local",
        "os_ed_desc": "_prefill_os_desc",
        "os_ed_concluido": "_prefill_os_concluido",
        "os_ed_obs": "_prefill_os_obs",
        "os_ed_dti": "_prefill_os_dti",
        "os_ed_ti": "_prefill_os_ti",
        "os_ed_dtf": "_prefill_os_dtf",
        "os_ed_tf": "_prefill_os_tf",
    }
    for widget_key, prefill_key in map_simple.items():
        if prefill_key in ss:
            ss[widget_key] = ss[prefill_key]


# ----------------- Setup -----------------
st.title("🧾 Ordens de Serviço (Corretiva)")
engine = get_engine()
T = TABLES["os"]
T_MO = TABLES["mo_os"]

maqs  = options_maquinas(engine)        # id, nome, ativo
funcs = options_funcionarios(engine)    # id, nome, cargo

MAQ_OPTS  = maqs["nome"].tolist() if not maqs.empty else []
FUNC_OPTS = funcs["nome"].tolist() if not funcs.empty else []

name2maqid  = {r["nome"]: int(r["id"]) for _, r in maqs.iterrows()} if not maqs.empty else {}
name2funcid = {r["nome"]: int(r["id"]) for _, r in funcs.iterrows()} if not funcs.empty else {}
id2maqname  = {int(r["id"]): r["nome"] for _, r in maqs.iterrows()} if not maqs.empty else {}
id2funcname = {int(r["id"]): r["nome"] for _, r in funcs.iterrows()} if not funcs.empty else {}

# Estado
if "os_edit_id" not in st.session_state:
    st.session_state["os_edit_id"] = None
if "os_ed_loaded_for" not in st.session_state:
    st.session_state["os_ed_loaded_for"] = None

# =====================================================
# 1) FORMULÁRIO — NOVA OS
# =====================================================
with st.expander("➕ Nova Ordem de Serviço", expanded=False):

    col1, col2, col3 = st.columns(3)
    with col1:
        if MAQ_OPTS:
            nome_maquina_new = st.selectbox("Máquina", MAQ_OPTS, key="os_new_maquina")
        else:
            nome_maquina_new = st.selectbox("Máquina", [], key="os_new_maquina_empty")
        resp_opts_new = ["—"] + FUNC_OPTS
        nome_func_new = st.selectbox("Responsável (opcional)", resp_opts_new, index=0, key="os_new_resp")
        tipo_new = st.text_input("Tipo de serviço", key="os_new_tipo")
    with col2:
        local_new = st.text_input("Local do problema", key="os_new_local")
        desc_new  = st.text_area("Descrição do problema", key="os_new_desc")
    with col3:
        dti_new = st.date_input("Data início", value=datetime.now().date(), key="os_new_dti")
        ti_new  = st.time_input("Hora início", value=datetime.now().time().replace(second=0, microsecond=0), key="os_new_ti")
        dtf_new = st.date_input("Data fim", value=datetime.now().date(), key="os_new_dtf")
        tf_new  = st.time_input("Hora fim", value=datetime.now().time().replace(second=0, microsecond=0), key="os_new_tf")
        concluido_new = st.number_input("Concluído (0/1)", 0, 1, 0, 1, key="os_new_concluido")
        obs_new = st.text_area("Observação", key="os_new_obs")

    cA, _ = st.columns([1, 5])
    with cA:
        if st.button("💾 Salvar nova OS", type="primary", use_container_width=True, key="os_btn_save_new"):
            maquina_escolhida = st.session_state.get("os_new_maquina") or st.session_state.get("os_new_maquina_empty")
            if not maquina_escolhida or not st.session_state.get("os_new_tipo"):
                st.error("Selecione a máquina e informe o tipo de serviço.")
            else:
                dt_ini = datetime.combine(st.session_state["os_new_dti"], st.session_state["os_new_ti"])
                dt_fim = datetime.combine(st.session_state["os_new_dtf"], st.session_state["os_new_tf"])
                if dt_fim < dt_ini:
                    st.error("Hora fim não pode ser menor que hora início.")
                else:
                    payload = {
                        "id_maquina": int(name2maqid.get(maquina_escolhida)) if maquina_escolhida else None,
                        "id_funcionario": (None if st.session_state["os_new_resp"] in ("—", "", None) else int(name2funcid.get(st.session_state["os_new_resp"]))),
                        "tipo_de_servico": st.session_state["os_new_tipo"],
                        "local_do_problema": st.session_state["os_new_local"],
                        "descricao_do_problema": st.session_state["os_new_desc"],
                        "datahora_inicio": dt_ini,
                        "datahora_fim": dt_fim,
                        "concluido": int(st.session_state["os_new_concluido"]),
                        "observacao": st.session_state["os_new_obs"],
                    }
                    insert_row(engine, T, payload)
                    st.success("OS inserida!")
                    st.rerun()



# ======================================================================
# 2) FORMULÁRIO — EDITAR OS (Selectbox + injeção _prefill)
# ======================================================================
with st.expander("✏️ Editar Ordem de Serviço", expanded=False):

    sql_sel = """
        SELECT os.id, m.nome AS maquina, os.tipo_de_servico, os.datahora_inicio
        FROM ordens_servico os
        JOIN maquinas m ON m.id = os.id_maquina
        ORDER BY os.datahora_inicio DESC, os.id DESC
        LIMIT 200
    """
    df_sel = fetch_df(engine, sql_sel, {})

    if df_sel.empty:
        st.info("Não há ordens para editar.")
        sel_id_quick = None
        st.session_state["os_edit_id"] = None
        st.session_state["os_ed_loaded_for"] = None
    else:
        opt_values = df_sel["id"].astype(int).tolist()
        opt_labels = df_sel.apply(
            lambda r: f"#{int(r['id'])} • {r['maquina']} • {r['tipo_de_servico']} • "
                    f"{pd.to_datetime(r['datahora_inicio'], errors='coerce').strftime('%d/%m %H:%M') if pd.notna(pd.to_datetime(r['datahora_inicio'], errors='coerce')) else ''}",
            axis=1
        ).tolist()

        idx_default = 0
        if st.session_state.get("os_edit_id") in opt_values:
            idx_default = opt_values.index(int(st.session_state["os_edit_id"]))

        sel_id_quick = st.selectbox(
            "🔎 Selecionar OS para edição",
            options=opt_values,
            format_func=lambda v: opt_labels[opt_values.index(v)],
            index=idx_default if len(opt_values) else 0,
            key="os_quick_select",
        )

        if sel_id_quick and st.session_state.get("os_ed_loaded_for") != int(sel_id_quick):
            rec = _load_os_record(engine, int(sel_id_quick))
            if rec:
                st.session_state["os_edit_id"] = int(sel_id_quick)
                _inject_edit_state(rec, id2maqname, id2funcname)
                _apply_os_prefill_to_widgets()
                st.session_state["os_ed_loaded_for"] = int(sel_id_quick)

        if st.session_state.get("os_ed_loaded_for") is None and sel_id_quick:
            rec = _load_os_record(engine, int(sel_id_quick))
            if rec:
                st.session_state["os_edit_id"] = int(sel_id_quick)
                _inject_edit_state(rec, id2maqname, id2funcname)
                _apply_os_prefill_to_widgets()
                st.session_state["os_ed_loaded_for"] = int(sel_id_quick)

    # Formulário de edição usando _prefill_*
    rec_ok = st.session_state.get("os_ed_loaded_for") is not None
    if not rec_ok:
        st.warning("Selecione uma OS para carregar os campos de edição.")
    else:
        col1e, col2e, col3e = st.columns(3)
        with col1e:
            if MAQ_OPTS:
                try:
                    idx_maq = MAQ_OPTS.index(st.session_state.get("_prefill_os_maquina_name", "")) if st.session_state.get("_prefill_os_maquina_name", "") in MAQ_OPTS else 0
                except Exception:
                    idx_maq = 0
                nome_maquina_ed = st.selectbox("Máquina", MAQ_OPTS, index=idx_maq, key="os_ed_maquina_name")
            else:
                nome_maquina_ed = st.selectbox("Máquina", [], key="os_ed_maquina_name")

            resp_opts_ed = ["—"] + FUNC_OPTS
            try:
                idx_resp = resp_opts_ed.index(st.session_state.get("_prefill_os_resp_name", "—")) if st.session_state.get("_prefill_os_resp_name", "—") in resp_opts_ed else 0
            except Exception:
                idx_resp = 0
            nome_func_ed = st.selectbox("Responsável (opcional)", resp_opts_ed, index=idx_resp, key="os_ed_resp_name")

            tipo_ed = st.text_input("Tipo de serviço", value=st.session_state.get("_prefill_os_tipo", ""), key="os_ed_tipo")

        with col2e:
            local_ed = st.text_input("Local do problema", value=st.session_state.get("_prefill_os_local", ""), key="os_ed_local")
            desc_ed  = st.text_area("Descrição do problema", value=st.session_state.get("_prefill_os_desc", ""), key="os_ed_desc")

        with col3e:
            dti_ed = st.date_input("Data início", value=st.session_state.get("_prefill_os_dti", datetime.now().date()), key="os_ed_dti")
            ti_ed  = st.time_input("Hora início", value=st.session_state.get("_prefill_os_ti", datetime.now().time().replace(second=0, microsecond=0)), key="os_ed_ti")
            dtf_ed = st.date_input("Data fim", value=st.session_state.get("_prefill_os_dtf", datetime.now().date()), key="os_ed_dtf")
            tf_ed  = st.time_input("Hora fim", value=st.session_state.get("_prefill_os_tf", datetime.now().time().replace(second=0, microsecond=0)), key="os_ed_tf")
            concluido_ed = st.number_input("Concluído (0/1)", 0, 1, int(st.session_state.get("_prefill_os_concluido", 0)), 1, key="os_ed_concluido")
            obs_ed = st.text_area("Observação", value=st.session_state.get("_prefill_os_obs", ""), key="os_ed_obs")

        cE1, cE2 = st.columns([1, 1])
        with cE1:
            if st.button("💾 Salvar edições", type="primary", use_container_width=True, key="os_btn_save_edit"):
                dt_ini = datetime.combine(st.session_state["os_ed_dti"], st.session_state["os_ed_ti"])
                dt_fim = datetime.combine(st.session_state["os_ed_dtf"], st.session_state["os_ed_tf"])
                if dt_fim < dt_ini:
                    st.error("Hora fim não pode ser menor que hora início.")
                else:
                    payload = {
                        "id": int(st.session_state["os_edit_id"]),
                        "id_maquina": int(name2maqid.get(st.session_state["os_ed_maquina_name"])) if st.session_state["os_ed_maquina_name"] else None,
                        "id_funcionario": (None if st.session_state["os_ed_resp_name"] in ("—", "", None) else int(name2funcid.get(st.session_state["os_ed_resp_name"]))),
                        "tipo_de_servico": st.session_state["os_ed_tipo"],
                        "local_do_problema": st.session_state["os_ed_local"],
                        "descricao_do_problema": st.session_state["os_ed_desc"],
                        "datahora_inicio": dt_ini,
                        "datahora_fim": dt_fim,
                        "concluido": int(st.session_state["os_ed_concluido"]),
                        "observacao": st.session_state["os_ed_obs"],
                    }
                    update_row(engine, T, "id", payload)
                    rec = _load_os_record(engine, int(st.session_state["os_edit_id"]))
                    if rec:
                        _inject_edit_state(rec, id2maqname, id2funcname)
                    st.success("OS alterada com sucesso!")
        with cE2:
            if st.button("🗑️ Excluir OS", type="secondary", use_container_width=True, key="os_btn_delete"):
                delete_by_ids(engine, T, [int(st.session_state["os_edit_id"])])
                st.success(f"OS #{int(st.session_state['os_edit_id'])} excluída.")
                # limpa estado e recarrega
                st.session_state["os_edit_id"] = None
                st.session_state["os_ed_loaded_for"] = None
                st.rerun()

# ======================================================================
# 2.1) MÃO DE OBRA — abaixo do formulário de edição (com edição/exclusão por linha)
# ======================================================================

with st.expander("🧑‍🔧 Mão de Obra da OS selecionada", expanded=False):

    os_id_ref = st.session_state.get("os_edit_id")
    try:
        os_id_ref = int(os_id_ref) if os_id_ref is not None else None
    except (TypeError, ValueError):
        os_id_ref = None

    if not os_id_ref:
        st.info("Selecione uma OS no seletor acima para lançar mão de obra.")
    else:
        st.caption(f"OS selecionada: **#{os_id_ref}**")

        # --- Formulário de inserção de MO ---
        with st.form("form_mo_os_inline"):
            colm1, colm2, colm3 = st.columns(3)
            with colm1:
                func_nome = st.selectbox("Funcionário", FUNC_OPTS, key="moos_func")
                func_id = name2funcid.get(func_nome) if func_nome else None
            with colm2:
                data_mo = st.date_input("Data", value=date.today(), key="moos_data")
                hi_mo   = st.time_input("Hora início", value=time(8, 0, 0), key="moos_hi")
                hf_mo   = st.time_input("Hora fim",    value=time(12, 0, 0), key="moos_hf")
            with colm3:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("➕ Inserir apontamento", type="primary", use_container_width=True)

            if submitted:
                if func_id is None:
                    st.error("Selecione o funcionário.")
                elif hf_mo < hi_mo:
                    st.error("Hora fim não pode ser menor que hora início (MO).")
                else:
                    insert_row(engine, T_MO, {
                        "id_ordem_servico": int(os_id_ref),
                        "id_funcionario": int(func_id),
                        "data": data_mo,
                        "hora_inicio": hi_mo,
                        "hora_fim": hf_mo
                    })
                    st.success("MO inserida!")
                    st.rerun()

    # --- Listagem de MOs da OS (com edição/exclusão) ---
with st.expander("🧑‍🔧🧑‍🔧 Mão de Obra Lançada", expanded=False):
    sql_mo = """
        SELECT mo.id, mo.id_funcionario, f.nome AS funcionario, mo.data, mo.hora_inicio, mo.hora_fim
        FROM mao_obra_os mo
        JOIN funcionarios f ON f.id = mo.id_funcionario
        WHERE mo.id_ordem_servico = :id
        ORDER BY mo.data ASC, mo.hora_inicio ASC
    """
    df_mo = fetch_df(engine, sql_mo, {"id": int(os_id_ref)})
    if df_mo.empty:
        st.info("Nenhum apontamento para esta OS.")
    else:
        for _, row in df_mo.iterrows():
            mo_id = int(row["id"])
            func_nome_row = str(row["funcionario"])
            idx_func = FUNC_OPTS.index(func_nome_row) if func_nome_row in FUNC_OPTS else 0

            with st.expander(f"MO #{mo_id} • {func_nome_row} • {row['data']} • {str(row['hora_inicio'])}–{str(row['hora_fim'])}", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    novo_func = st.selectbox("Funcionário", FUNC_OPTS, index=idx_func, key=f"moos_edit_func_{mo_id}")
                with c2:
                    nova_data = st.date_input("Data", value=pd.to_datetime(str(row["data"])).date(), key=f"moos_edit_data_{mo_id}")
                with c3:
                    novo_hi = st.time_input("Hora início", value=_as_time(row["hora_inicio"]), key=f"moos_edit_hi_{mo_id}")
                with c4:
                    novo_hf = st.time_input("Hora fim", value=_as_time(row["hora_fim"]), key=f"moos_edit_hf_{mo_id}")

                cA, cB = st.columns(2)
                with cA:
                    if st.button("💾 Salvar", key=f"moos_btn_save_{mo_id}", use_container_width=True):
                        if novo_hf < novo_hi:
                            st.error("Hora fim não pode ser menor que hora início.")
                        else:
                            update_row(engine, T_MO, "id", {
                                "id": mo_id,
                                "id_funcionario": int(name2funcid.get(novo_func)),
                                "data": nova_data,
                                "hora_inicio": novo_hi,
                                "hora_fim": novo_hf
                            })
                            st.success("Apontamento atualizado.")
                            st.rerun()
                with cB:
                    if st.button("🗑️ Excluir", key=f"moos_btn_del_{mo_id}", use_container_width=True):
                        delete_by_ids(engine, T_MO, [mo_id])
                        st.success("Apontamento excluído.")
                        st.rerun()

# =========================================
# 3) FILTROS (para a listagem)
# =========================================
with st.expander("🔎 Filtros", expanded=False):
    f_maquina = st.selectbox("Máquina", ["Todas"] + MAQ_OPTS, key="os_f_maquina")
    f_concl   = st.selectbox("Concluída?", ["Todas", "Somente abertas (0)", "Somente concluídas (1)"], key="os_f_concl")
    f_dt_ini  = st.date_input("Data inicial", value=datetime.now().date() - timedelta(days=30), key="os_f_di")
    f_dt_fim  = st.date_input("Data final", value=datetime.now().date(), key="os_f_df")
    page_size = st.number_input("Itens por página", 5, 200, 25, 5, key="os_page_size")

where, params = ["WHERE 1=1"], {}
if f_maquina != "Todas" and f_maquina in name2maqid:
    where.append("AND os.id_maquina = :m"); params["m"] = name2maqid[f_maquina]
if f_concl == "Somente abertas (0)":
    where.append("AND os.concluido = 0")
elif f_concl == "Somente concluídas (1)":
    where.append("AND os.concluido = 1")
if f_dt_ini:
    where.append("AND os.datahora_inicio >= :di"); params["di"] = datetime(f_dt_ini.year, f_dt_ini.month, f_dt_ini.day, 0, 0, 0)
if f_dt_fim:
    where.append("AND os.datahora_inicio <= :df"); params["df"] = datetime(f_dt_fim.year, f_dt_fim.month, f_dt_fim.day, 23, 59, 59)

where_sql = " " + " ".join(where)
order_sql = " ORDER BY os.datahora_inicio DESC, os.id DESC"
total = count_rows(engine, T + " os", where_sql, params)
st.caption(f"Total com filtros: **{total}**")

# =========================================
# 4) TABELA (sem checkbox de seleção)
# =========================================
page = st.number_input("Página", 1, max(1, (total - 1) // st.session_state["os_page_size"] + 1), 1, key="os_page")
offset = (page - 1) * st.session_state["os_page_size"]

sql_list = f"""
    SELECT
      os.id,
      m.nome           AS maquina,
      f.nome           AS responsavel,
      os.tipo_de_servico,
      os.local_do_problema,
      os.descricao_do_problema,
      os.datahora_inicio,
      os.datahora_fim,
      os.concluido,
      os.observacao
    FROM {T} os
    JOIN maquinas m           ON m.id = os.id_maquina
    LEFT JOIN funcionarios f  ON f.id = os.id_funcionario
    {where_sql}{order_sql}
    LIMIT :lim OFFSET :off
"""
df_list = fetch_df(engine, sql_list, {**params, "lim": int(st.session_state["os_page_size"]), "off": int(offset)})

st.subheader("📋 Listagem")
if df_list.empty:
    st.info("Nada encontrado com os filtros.")
else:
    st.dataframe(df_list, use_container_width=True)
    st.download_button(
        "⬇️ Exportar CSV",
        df_list.to_csv(index=False).encode("utf-8"),
        "ordens_servico.csv",
        "text/csv",
        use_container_width=True,
        key="os_btn_csv"
    )
